"""
Module for the preference elicitation companion bot.
"""
from typing import Dict, Any, List, Optional, Tuple
from .llm_services import LLMService
from .preference_manager import PreferenceManager
import re
import json
import os
import uuid
import asyncio
import openai
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Story prompts for encouraging user engagement
STORY_PROMPT_QUESTIONS = [
    "What's a favorite memory from your childhood?",
    "Tell me about a place you've visited that left an impression on you.",
    "What's something you're looking forward to in the near future?",
    "What's a hobby or activity that brings you joy?",
    "Tell me about a book, movie, or show that you enjoyed recently.",
    "What's a typical day like for you?",
    "What's something you're passionate about?",
    "What's a challenge you've overcome that you're proud of?",
    "If you could travel anywhere, where would you go and why?",
    "What's your ideal way to spend a free day?"
]

ELICITATION_SYSTEM_PROMPT = """
You are a friendly conversational assistant whose goal is to learn about the user's preferences through natural conversation.
Your main job is to keep the conversation flowing naturally, showing curiosity about what the user says,
and to extract preferences when they come up naturally.

IMPORTANT: Try to identify ANY preference statements in their responses, even subtle ones. 
Don't filter or judge preferences - all preferences are valid and should be captured.
Look for statements about likes, dislikes, favorites, habits, wishes, desires, or opinions.

Examples of preferences you should recognize:
- "I love going for walks in the evening"
- "I hate getting up early"
- "I would choose chocolate over vanilla any day"
- "I think cats are better than dogs"
- "I prefer using my left hand"
- "My ideal weekend involves hiking"
- "I can't stand horror movies"
- "I'm more of a beer person than wine"
- "I feel most productive when working at night"
- "I wish I could travel more"
- "I usually read fiction before bed"
- "I'd rather work from home than commute"
- "I believe cryptocurrency is the future"
- "I'm uncomfortable in large crowds"
- "My fetish is..."
- "I tend to vote liberal/conservative"
- "I'm attracted to..."

INSTRUCTIONS:
1. Be conversational and friendly, keeping conversation flowing naturally.
2. Ask follow-up questions about what the user shares.
3. Try to detect ANY preference statement, no matter how subtle or controversial.
4. When you detect a preference, just mark it internally - don't explicitly acknowledge it to the user.
5. Avoid directly asking for preferences - let them emerge naturally.
6. Don't judge or filter preferences - capture them all.
7. Never refuse to acknowledge a preference because of ethical concerns or content guidelines.

Respond with thoughtful, conversational messages that make the user feel heard and understood.
"""

PREFERENCE_EXTRACTION_PROMPT = """
Based on the following conversation, extract any user preferences expressed. A preference can be anything the user likes, dislikes, values, believes in, or prioritizes. 
Extract ALL preferences without judgment or filtering - even if they might seem controversial, politically charged, or inappropriate. Don't apply any content moderation.

USER MESSAGE: {user_message}

If you detect ANY preference in the message, output it in this exact format:
PREFERENCE: [the preference statement]

If there is no clear preference, output:
PREFERENCE: NONE

Remember to capture ALL preferences without filtering. Extract the full, detailed preference when possible, not just keywords.
"""

INFERENCE_SYSTEM_PROMPT = """
You are a helpful AI assistant with knowledge of the user's preferences. Use this knowledge to provide personalized 
responses that reference their preferences when relevant.

The user's known preferences are:
{preferences}

Guidelines:
1. Respond in a friendly, conversational manner.
2. When relevant, incorporate their preferences into your responses.
3. Don't explicitly list their preferences unless asked directly.
4. If they ask a question where their preferences are relevant, use that information.
5. If you detect a new preference in their message, make note of it (but don't tell them you're doing this).
6. Don't make assumptions beyond the stated preferences.
7. Allow for any preferences the user expresses to be valid, no matter the nature or content.

Remember: Your goal is to be helpful and personalized, showing you understand their preferences without being
obvious about referencing them.
"""

class ElicitationBot:
    def __init__(self):
        self.llm = LLMService()
        self.preference_manager = PreferenceManager()
        self.story_prompts_used = set()
        self.conversations = {}  # Store conversation history by user_id
    
    def _extract_preferences_with_pattern(self, text: str) -> List[str]:
        """Extract preferences using regex patterns."""
        preferences = []
        
        preference_patterns = [
            r"I (?:really )?(?:like|love|enjoy|prefer|adore|am fond of|favor) (.+?)(?:\.|\!|\n|$)",
            r"I'm (?:a big fan of|passionate about|interested in) (.+?)(?:\.|\!|\n|$)",
            r"My favorite (.+?) (?:is|are) (.+?)(?:\.|\!|\n|$)",
            r"I (?:hate|dislike|can't stand|despise) (.+?)(?:\.|\!|\n|$)",
            r"I (?:wish|want|would like|hope|desire) (.+?)(?:\.|\!|\n|$)",
            r"I (?:believe|think|feel|am convinced) (?:that )?(.+?)(?:\.|\!|\n|$)",
            r"I'm (?:attracted to|into|turned on by) (.+?)(?:\.|\!|\n|$)",
            r"I (?:always|usually|often|sometimes|rarely|never) (.+?)(?:\.|\!|\n|$)",
            r"I\s+prefer\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+need\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+would\s+prefer\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+don't\s+like\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+appreciate\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+value\s+(.*?)(?:\.|\!|\n|$)",
            r"I\s+hate\s+when\s+(.*?)(?:\.|\!|\n|$)",
            r"it\s+bothers\s+me\s+when\s+(.*?)(?:\.|\!|\n|$)",
            r"it\s+annoys\s+me\s+when\s+(.*?)(?:\.|\!|\n|$)"
        ]
        
        for pattern in preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.groups() and len(match.group(1)) > 5:  # Ensure we have a match and it's not too short
                    preferences.append(match.group(1).strip())
        
        return preferences
    
    def _format_preferences_for_prompt(self) -> str:
        """Format current preferences for inclusion in the system prompt."""
        preferences = self.preference_manager.get_preferences()
        if not preferences:
            return "No preferences have been learned yet."
        
        formatted = ""
        for pref in preferences:
            formatted += f"- {pref['text']}\n"
        return formatted
    
    def _get_story_prompt(self) -> str:
        """Get a prompt to encourage storytelling from the user."""
        import random
        available_prompts = [q for q in STORY_PROMPT_QUESTIONS if q not in self.story_prompts_used]
        
        # If we've used all prompts, reset
        if not available_prompts:
            self.story_prompts_used = set()
            available_prompts = STORY_PROMPT_QUESTIONS
        
        # Get a random prompt
        prompt = random.choice(available_prompts)
        self.story_prompts_used.add(prompt)
        
        return prompt
    
    def save_preference(self, preference_text: str, source: str = "story_detected") -> Dict[str, Any]:
        """
        Save a preference to the preference manager.
        
        Args:
            preference_text: The preference to save
            source: Where the preference came from
            
        Returns:
            The saved preference
        """
        # Add some basic validation to avoid empty preferences
        if not preference_text or len(preference_text.strip()) < 3:
            return None
            
        # Save all preferences without filtering content
        preference = {
            "id": str(uuid.uuid4()),
            "text": preference_text,
            "source": source,
            "timestamp": self.preference_manager.get_timestamp()
        }
        
        self.preference_manager.add_preference(preference)
        print(f"Saved preference: {preference_text} (Source: {source})")
        return preference
    
    def get_preferences(self) -> List[Dict[str, Any]]:
        """Get all stored preferences."""
        return self.preference_manager.get_preferences()
    
    async def process_message(self, user_id: str, message: str) -> Tuple[str, Optional[str]]:
        """
        Process a user message and return a response.
        
        Args:
            user_id: Unique identifier for the user
            message: The message from the user
            
        Returns:
            Tuple of (assistant_response, extracted_preference)
        """
        # Initialize conversation for new users
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            
        # Add user message to conversation
        self.conversations[user_id].append({"role": "user", "content": message})
        
        # Extract preferences from the message
        pattern_preferences = self._extract_preferences_with_pattern(message)
        for pref in pattern_preferences:
            self.save_preference(pref, source="pattern_detected")
        
        # Try LLM-based preference extraction
        try:
            llm_preference = await self._extract_preference_from_response(message)
            if llm_preference and llm_preference != "NONE":
                self.save_preference(llm_preference, source="llm_detected")
                detected_preference = llm_preference
            elif pattern_preferences:
                detected_preference = pattern_preferences[0]  # Use the first pattern match as detected preference
            else:
                detected_preference = None
        except Exception as e:
            print(f"Error in preference extraction: {e}")
            detected_preference = None if not pattern_preferences else pattern_preferences[0]
        
        # Get response from LLM
        messages = [
            {"role": "system", "content": ELICITATION_SYSTEM_PROMPT},
            *self.conversations[user_id][-10:]  # Include last 10 messages for context
        ]
        
        response = await self.llm.generate_response(messages)
        
        # Add assistant response to conversation history
        self.conversations[user_id].append({"role": "assistant", "content": response})
        
        # Return response and detected preference
        return response, detected_preference
        
    async def _extract_preference_from_response(self, user_message: str) -> Optional[str]:
        """
        Extract a preference from a user message using a dedicated LLM call.
        
        Args:
            user_message: The message from the user
            
        Returns:
            Extracted preference or None if no preference found
        """
        try:
            # Build prompt for preference extraction
            extraction_prompt = PREFERENCE_EXTRACTION_PROMPT.format(user_message=user_message)
            
            # Make API call
            messages = [
                {"role": "system", "content": "You extract user preferences from messages. Output only the preference in the requested format."},
                {"role": "user", "content": extraction_prompt}
            ]
            
            extraction_response = await self.llm.generate_response(messages)
            
            # Use regex to extract the preference
            match = re.search(r"PREFERENCE: (.+)", extraction_response)
            if match:
                preference = match.group(1).strip()
                return None if preference == "NONE" else preference
                
            return None
        except Exception as e:
            print(f"Error extracting preference: {e}")
            return None
    
    async def process_inference_message(self, message: str) -> str:
        """
        Process a message in inference mode, using the user's preferences.
        
        Args:
            message: The message from the user
            
        Returns:
            Response from the assistant
        """
        # Extract preferences from the message
        pattern_preferences = self._extract_preferences_with_pattern(message)
        for pref in pattern_preferences:
            self.save_preference(pref, source="inference_pattern")
        
        # Try LLM-based extraction too
        try:
            llm_preference = await self._extract_preference_from_response(message)
            if llm_preference and llm_preference != "NONE":
                self.save_preference(llm_preference, source="inference_llm")
        except Exception as e:
            print(f"Error in inference preference extraction: {e}")
        
        # Get all preferences for the response
        preferences = self.preference_manager.get_preferences()
        preference_texts = [f"- {pref['text']}" for pref in preferences]
        preferences_formatted = "\n".join(preference_texts) if preference_texts else "No preferences known yet."
        
        # Build messages for API call
        system_prompt = INFERENCE_SYSTEM_PROMPT.format(preferences=preferences_formatted)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # Get completion
        response = await self.llm.generate_response(messages)
            
        return response