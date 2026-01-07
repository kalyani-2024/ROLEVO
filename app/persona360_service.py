"""
Persona360 Voice Analysis Service
Provides 16PF (Sixteen Personality Factor) scores based on audio analysis.

API Documentation:
- Endpoint: http://api.persona360.rapeti.dev:8290/predict
- Method: POST (multipart/form-data)
- Parameters:
  - file: Audio/video file for analysis
  - mode: "audio_only" for voice-based analysis
  - age: User's age (string)
  - gender: "Male" or "Female"
"""

import os
import requests
from typing import Dict, Optional, Tuple, Any
import json


class Persona360Service:
    """Service class for interacting with Persona360 API for 16PF voice analysis."""
    
    # Default API endpoint
    DEFAULT_API_URL = "http://api.persona360.rapeti.dev:8290/predict"
    
    # 16PF Personality Factors
    PERSONALITY_FACTORS = [
        "Warmth",               # Factor A
        "Reasoning",            # Factor B
        "Emotional Stability",  # Factor C
        "Dominance",            # Factor E
        "Liveliness",           # Factor F
        "Rule-Consciousness",   # Factor G
        "Social Boldness",      # Factor H
        "Sensitivity",          # Factor I
        "Vigilance",            # Factor L
        "Abstractedness",       # Factor M
        "Privateness",          # Factor N
        "Apprehension",         # Factor O
        "Openness to Change",   # Factor Q1
        "Self-Reliance",        # Factor Q2
        "Perfectionism",        # Factor Q3
        "Tension",              # Factor Q4
    ]
    
    # Additional composite/derived scores
    COMPOSITE_SCORES = [
        "Adjustment",
        "Agreeableness",
        "Ambition",
        "Communication",
        "Conscientiousness",
        "Cooperation",
        "Creativity",
        "Technology Fit",
        "Sales Fit",
        "Management Fit",
        "Customer Service Fit",
    ]
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Persona360 service.
        
        Args:
            api_url: Custom API URL (uses default if not provided)
            api_key: API key for authentication (if required)
        """
        self.api_url = api_url or os.getenv('PERSONA360_API_URL', self.DEFAULT_API_URL)
        self.api_key = api_key or os.getenv('PERSONA360_API_KEY', '')
        self.timeout = int(os.getenv('PERSONA360_TIMEOUT', 120))  # 2 minute timeout for audio processing
    
    def analyze_audio(self, file_path: str, age: int = 30, gender: str = "Male",
                      mode: str = "audio_only") -> Tuple[bool, Dict[str, Any]]:
        """
        Analyze audio file for 16PF personality traits.
        
        Args:
            file_path: Path to the audio/video file
            age: User's age (default: 30)
            gender: "Male" or "Female" (default: "Male")
            mode: Analysis mode - "audio_only" or "video" (default: "audio_only")
        
        Returns:
            Tuple of (success: bool, result: dict)
            On success: (True, {"personality_scores": {...}, "overall_fit": float, ...})
            On failure: (False, {"error": "error message"})
        """
        # Validate file exists
        if not os.path.exists(file_path):
            return False, {"error": f"File not found: {file_path}"}
        
        # Validate gender
        gender = gender.capitalize()
        if gender not in ["Male", "Female"]:
            gender = "Male"  # Default to Male if invalid
        
        try:
            # Prepare the request
            headers = {
                "accept": "application/json"
            }
            
            # Add API key if configured
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Prepare form data
            data = {
                "mode": mode,
                "age": str(age),
                "gender": gender
            }
            
            # Open file and send request
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(file_path), audio_file)
                }
                
                print(f"[Persona360] Sending audio for analysis: {file_path}")
                print(f"[Persona360] Parameters: age={age}, gender={gender}, mode={mode}")
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
            
            # Check response status
            if response.status_code == 200:
                result = response.json()
                print(f"[Persona360] Analysis successful: {json.dumps(result, indent=2)[:500]}...")
                return True, self._parse_response(result)
            else:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                print(f"[Persona360] Error: {error_msg}")
                return False, {"error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.timeout} seconds"
            print(f"[Persona360] Error: {error_msg}")
            return False, {"error": error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"[Persona360] Error: {error_msg}")
            return False, {"error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[Persona360] Error: {error_msg}")
            return False, {"error": error_msg}
    
    def _parse_response(self, api_response: Dict) -> Dict[str, Any]:
        """
        Parse the API response and normalize it to our expected format.
        
        Args:
            api_response: Raw response from Persona360 API
        
        Returns:
            Normalized response dictionary
        """
        result = {
            "raw_response": api_response,
            "personality_scores": {},
            "composite_scores": {},
            "overall_role_fit": None,
            "analysis_confidence": None
        }
        
        # The API response structure may vary - handle common formats
        # Try to extract personality factors
        if "personality" in api_response:
            personality_data = api_response["personality"]
            if isinstance(personality_data, dict):
                result["personality_scores"] = personality_data
        
        # Try to extract 16PF factors directly
        if "16pf" in api_response:
            result["personality_scores"] = api_response["16pf"]
        
        # Try to extract factor scores
        if "factors" in api_response:
            result["personality_scores"] = api_response["factors"]
        
        # Extract composite scores if present
        for score_name in self.COMPOSITE_SCORES:
            score_key = score_name.lower().replace(" ", "_")
            if score_key in api_response:
                result["composite_scores"][score_name] = api_response[score_key]
            elif score_name in api_response:
                result["composite_scores"][score_name] = api_response[score_name]
        
        # Extract overall fit scores
        for fit_key in ["overall_fit", "role_fit", "overall_role_fit", "fit_score"]:
            if fit_key in api_response:
                result["overall_role_fit"] = api_response[fit_key]
                break
        
        # Extract confidence if available
        for conf_key in ["confidence", "analysis_confidence", "score_confidence"]:
            if conf_key in api_response:
                result["analysis_confidence"] = api_response[conf_key]
                break
        
        # If the API returns scores directly at the root level, try to map them
        if not result["personality_scores"] and not result["composite_scores"]:
            # Try to find any score-like values in the response
            for key, value in api_response.items():
                if isinstance(value, (int, float)) and 0 <= value <= 100:
                    # Normalize key name
                    normalized_key = key.replace("_", " ").title()
                    if normalized_key in self.PERSONALITY_FACTORS:
                        result["personality_scores"][normalized_key] = value
                    elif normalized_key in self.COMPOSITE_SCORES:
                        result["composite_scores"][normalized_key] = value
                    else:
                        # Add to composite scores as a custom metric
                        result["composite_scores"][normalized_key] = value
        
        return result
    
    def get_personality_for_report(self, analysis_result: Dict) -> list:
        """
        Format personality analysis results for the report generator.
        
        Args:
            analysis_result: Result from analyze_audio()
        
        Returns:
            List of tuples: [(trait_name, score, target_score), ...]
        """
        personality_data = []
        
        # Add personality factor scores
        for trait, score in analysis_result.get("personality_scores", {}).items():
            # Default target score of 70% for all traits
            target = 70
            personality_data.append((trait, score, target))
        
        # Add composite scores
        for trait, score in analysis_result.get("composite_scores", {}).items():
            target = 70
            personality_data.append((trait, score, target))
        
        return personality_data
    
    def is_available(self) -> bool:
        """
        Check if the Persona360 API is available and reachable.
        
        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try a simple HEAD request to check availability
            response = requests.head(self.api_url, timeout=5)
            return response.status_code in [200, 405]  # 405 = Method Not Allowed is OK for HEAD
        except:
            return False


# Singleton instance for easy access
_persona360_service = None


def get_persona360_service() -> Persona360Service:
    """Get or create the Persona360 service singleton."""
    global _persona360_service
    if _persona360_service is None:
        _persona360_service = Persona360Service()
    return _persona360_service


def analyze_audio_for_16pf(file_path: str, age: int = 30, gender: str = "Male") -> Tuple[bool, Dict]:
    """
    Convenience function to analyze audio for 16PF traits.
    
    Args:
        file_path: Path to audio/video file
        age: User's age
        gender: "Male" or "Female"
    
    Returns:
        Tuple of (success, result_dict)
    """
    service = get_persona360_service()
    return service.analyze_audio(file_path, age=age, gender=gender)
