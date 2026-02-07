"""
Persona360 Voice Analysis Service
Provides 16PF (Sixteen Personality Factor) scores based on audio analysis.

API Documentation:
- Endpoint: http://api.persona360.rapeti.dev:8290/predict
- Method: POST (multipart/form-data)
- Parameters:
  - file: Audio/video file for analysis
  - mode: "audio", "video", or "multimodal"
  - age: User's age (string)
  - gender: "Male" or "Female"
"""

import os
import socket
import requests
from typing import Dict, Optional, Tuple, Any
import json


# Custom DNS resolution - fallback to known IP if DNS fails
def _resolve_persona360_host():
    """Try to resolve the Persona360 host, fall back to known IP if DNS fails."""
    hostname = "api.persona360.rapeti.dev"
    try:
        socket.gethostbyname(hostname)
        return hostname  # DNS works, use hostname
    except socket.gaierror:
        print(f"[Persona360] DNS resolution failed for {hostname}, using direct IP")
        return "217.164.6.105"  # Known IP fallback


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
    
    # 16PF Factor code to name mapping
    FACTOR_CODE_TO_NAME = {
        "A": "Warmth",
        "B": "Reasoning", 
        "C": "Emotional Stability",
        "E": "Dominance",
        "F": "Liveliness",
        "G": "Rule-Consciousness",
        "H": "Social Boldness",
        "I": "Sensitivity",
        "L": "Vigilance",
        "M": "Abstractedness",
        "N": "Privateness",
        "O": "Apprehension",
        "Q1": "Openness to Change",
        "Q2": "Self-Reliance",
        "Q3": "Perfectionism",
        "Q4": "Tension",
    }
    
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
    
    def _get_api_url_with_fallback(self) -> Tuple[str, Dict[str, str]]:
        """
        Get the API URL, falling back to direct IP if DNS fails.
        Returns (url, extra_headers) where extra_headers contains Host header if using IP.
        """
        original_url = self.api_url
        extra_headers = {}
        
        # Check if we can resolve the hostname
        if "api.persona360.rapeti.dev" in original_url:
            resolved_host = _resolve_persona360_host()
            if resolved_host != "api.persona360.rapeti.dev":
                # DNS failed, use IP with Host header
                url = original_url.replace("api.persona360.rapeti.dev", resolved_host)
                extra_headers["Host"] = "api.persona360.rapeti.dev:8290"
                print(f"[Persona360] Using fallback IP: {url}")
                return url, extra_headers
        
        return original_url, extra_headers
    
    def analyze_audio(self, file_path: str, age: int = None, gender: str = None,
                      mode: str = "audio") -> Tuple[bool, Dict[str, Any]]:
        """
        Analyze audio file for 16PF personality traits.
        
        Args:
            file_path: Path to the audio/video file
            age: User's age (optional - not required by API)
            gender: "Male" or "Female" (optional - not required by API)
            mode: Analysis mode - "audio", "video", or "multimodal" (default: "audio")
        
        Returns:
            Tuple of (success: bool, result: dict)
            On success: (True, {"personality_scores": {...}, "overall_fit": float, ...})
            On failure: (False, {"error": "error message"})
        """
        # Validate file exists
        if not os.path.exists(file_path):
            return False, {"error": f"File not found: {file_path}"}
        
        try:
            # Get URL with DNS fallback
            api_url, extra_headers = self._get_api_url_with_fallback()
            
            # Prepare the request
            headers = {
                "accept": "application/json"
            }
            headers.update(extra_headers)
            
            # Add API key if configured
            if self.api_key:
                headers["x-api-key"] = self.api_key
            
            # Prepare form data - only include mode, age and gender are optional
            data = {
                "mode": mode
            }
            
            # Only add age and gender if provided
            if age is not None:
                data["age"] = str(age)
            if gender is not None:
                gender = gender.capitalize()
                if gender in ["Male", "Female"]:
                    data["gender"] = gender
            
            # Open file and send request
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(file_path), audio_file)
                }
                
                print(f"[Persona360] Sending audio for analysis: {file_path}")
                print(f"[Persona360] API URL: {api_url}")
                print(f"[Persona360] Parameters: {data}")
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
            
            # Check response status
            if response.status_code == 200:
                result = response.json()
                print(f"[Persona360] Analysis successful!")
                print(f"[Persona360] FULL RAW RESPONSE: {json.dumps(result, indent=2)}")
                print(f"[Persona360] Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
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
        
        print(f"[Persona360] Parsing response with keys: {list(api_response.keys()) if isinstance(api_response, dict) else 'Not a dict'}")
        
        # The API response structure may vary - handle common formats
        # Try to extract personality factors
        if "personality" in api_response:
            personality_data = api_response["personality"]
            print(f"[Persona360] Found 'personality' key with {len(personality_data) if isinstance(personality_data, dict) else 'non-dict'} items")
            if isinstance(personality_data, dict):
                result["personality_scores"] = personality_data
        
        # Try to extract 16PF factors directly
        if "16pf" in api_response:
            print(f"[Persona360] Found '16pf' key")
            result["personality_scores"] = api_response["16pf"]
        
        # Try to extract factor scores
        if "factors" in api_response:
            print(f"[Persona360] Found 'factors' key")
            result["personality_scores"] = api_response["factors"]
        
        # Try "scores" key
        if "scores" in api_response:
            print(f"[Persona360] Found 'scores' key: {api_response['scores']}")
            if isinstance(api_response["scores"], dict):
                result["personality_scores"] = api_response["scores"]
        
        # Try "traits" key
        if "traits" in api_response:
            print(f"[Persona360] Found 'traits' key: {api_response['traits']}")
            if isinstance(api_response["traits"], dict):
                result["personality_scores"] = api_response["traits"]
        
        # Try "predictions" or "results" keys - THIS IS THE MAIN FORMAT FROM PERSONA360 API
        if "predictions" in api_response:
            predictions = api_response["predictions"]
            print(f"[Persona360] Found 'predictions' key: {predictions}")
            if isinstance(predictions, dict):
                # Convert factor codes (A, B, C...) to full names (Warmth, Reasoning...)
                for code, score in predictions.items():
                    if code in self.FACTOR_CODE_TO_NAME:
                        full_name = self.FACTOR_CODE_TO_NAME[code]
                        result["personality_scores"][full_name] = score
                        print(f"[Persona360] Mapped {code} -> {full_name} = {score}")
                    else:
                        # Keep as-is if not a known code
                        result["personality_scores"][code] = score
                        print(f"[Persona360] Kept unknown code {code} = {score}")
        
        if "results" in api_response:
            print(f"[Persona360] Found 'results' key: {api_response['results']}")
            if isinstance(api_response["results"], dict):
                result["personality_scores"] = api_response["results"]
        
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
        
        print(f"[Persona360] FINAL parsed personality_scores: {result['personality_scores']}")
        print(f"[Persona360] FINAL parsed composite_scores: {result['composite_scores']}")
        print(f"[Persona360] FINAL overall_role_fit: {result['overall_role_fit']}")
        
        # If the API returns scores directly at the root level and we haven't found them yet, try to map them
        if not result["personality_scores"]:
            print(f"[Persona360] No personality scores found in standard keys, checking root level...")
            # Try to find any score-like values in the response
            for key, value in api_response.items():
                # print(f"[Persona360] Checking key '{key}': value={value}, type={type(value)}")
                if isinstance(value, (int, float)) and 0 <= value <= 100:
                    # Normalize key name
                    normalized_key = key.replace("_", " ").title()
                    
                    # Direct match or case-insensitive match
                    if normalized_key in self.PERSONALITY_FACTORS:
                        result["personality_scores"][normalized_key] = value
                        print(f"[Persona360] Mapped '{key}' -> personality_scores['{normalized_key}'] = {value}")
                    elif normalized_key in self.COMPOSITE_SCORES:
                        result["composite_scores"][normalized_key] = value
                        print(f"[Persona360] Mapped '{key}' -> composite_scores['{normalized_key}'] = {value}")
                    
                    # Also check against FACTOR_CODE_TO_NAME (e.g. key="A" -> Warmth)
                    elif key in self.FACTOR_CODE_TO_NAME:
                        full_name = self.FACTOR_CODE_TO_NAME[key]
                        result["personality_scores"][full_name] = value
                        print(f"[Persona360] Mapped code '{key}' -> personality_scores['{full_name}'] = {value}")
                        
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


def analyze_audio_for_16pf(file_path: str, age: int = None, gender: str = None) -> Tuple[bool, Dict]:
    """
    Convenience function to analyze audio for 16PF traits.
    
    Args:
        file_path: Path to audio/video file
        age: User's age (optional)
        gender: "Male" or "Female" (optional)
    
    Returns:
        Tuple of (success, result_dict)
    """
    service = get_persona360_service()
    return service.analyze_audio(file_path, age=age, gender=gender)
