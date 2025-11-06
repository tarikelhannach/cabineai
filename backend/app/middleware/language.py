"""
Language Detection Middleware for Internationalization
Detects and sets the user's preferred language from Accept-Language header
"""

from fastapi import Request
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware


class LanguageMiddleware(BaseHTTPMiddleware):
    """
    Middleware that detects the user's language preference from:
    1. Accept-Language HTTP header
    2. User's saved language preference (if authenticated)
    3. Firm's default language (if authenticated)
    4. Fallback to French (fr)
    
    Supported languages: English (en), French (fr), Arabic (ar)
    """
    
    SUPPORTED_LANGUAGES = ["en", "fr", "ar"]
    DEFAULT_LANGUAGE = "fr"
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Try to detect language from Accept-Language header
        accept_language = request.headers.get("Accept-Language", "")
        detected_language = self._parse_accept_language(accept_language)
        
        # If user is authenticated, check their saved preference
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            
            # User's personal language preference takes highest priority
            if hasattr(user, "language") and user.language:
                detected_language = user.language.value if hasattr(user.language, "value") else str(user.language)
            
            # If no personal preference, use firm's default
            elif hasattr(user, "firm") and user.firm and hasattr(user.firm, "language_preference"):
                firm_lang = user.firm.language_preference
                detected_language = firm_lang.value if hasattr(firm_lang, "value") else str(firm_lang)
        
        # Ensure the language is supported
        if detected_language not in self.SUPPORTED_LANGUAGES:
            detected_language = self.DEFAULT_LANGUAGE
        
        # Store language in request state for use in routes
        request.state.language = detected_language
        
        # Also set it as a custom header for the response
        response = await call_next(request)
        response.headers["Content-Language"] = detected_language
        
        return response
    
    def _parse_accept_language(self, accept_language: str) -> str:
        """
        Parse Accept-Language header and return the best matching supported language.
        
        Example: "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ar;q=0.6" -> "fr"
        """
        if not accept_language:
            return self.DEFAULT_LANGUAGE
        
        # Parse Accept-Language header
        languages = []
        for lang_str in accept_language.split(","):
            parts = lang_str.strip().split(";")
            lang_code = parts[0].split("-")[0].lower()  # Get base language code (e.g., "fr" from "fr-FR")
            
            # Extract quality value (default to 1.0)
            quality = 1.0
            if len(parts) > 1 and parts[1].startswith("q="):
                try:
                    quality = float(parts[1][2:])
                except ValueError:
                    quality = 1.0
            
            if lang_code in self.SUPPORTED_LANGUAGES:
                languages.append((lang_code, quality))
        
        # Sort by quality value (highest first)
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # Return the highest quality supported language
        if languages:
            return languages[0][0]
        
        return self.DEFAULT_LANGUAGE


def get_current_language(request: Request) -> str:
    """
    Helper function to get the current language from request state.
    Can be used in route dependencies for translations.
    """
    return getattr(request.state, "language", "fr")
