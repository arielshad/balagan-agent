#!/usr/bin/env python3
"""Validate Google Gemini API key from .env file.

This script checks if your GOOGLE_API_KEY or GEMINI_TOKEN is valid by making
a simple test request to the Gemini API.
"""

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("Attempting to use environment variables directly...\n")


def validate_gemini_key() -> tuple[bool, str]:
    """Validate the Gemini API key by making a test request.

    Returns:
        Tuple of (is_valid, message)
    """
    # Check if API key exists in environment
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_TOKEN")

    if not api_key:
        return False, (
            "❌ No API key found in environment.\n"
            "   Set GOOGLE_API_KEY or GEMINI_TOKEN in your .env file.\n"
            "   Get a key from: https://aistudio.google.com/app/apikey"
        )

    # Check basic format
    if not api_key.startswith("AIza"):
        return False, (
            f"❌ API key format looks invalid: {api_key[:10]}...\n"
            "   Valid keys start with 'AIza' and are 39 characters long.\n"
            "   Get a key from: https://aistudio.google.com/app/apikey"
        )

    if len(api_key) != 39:
        return False, (
            f"❌ API key length is {len(api_key)}, expected 39 characters.\n"
            "   Valid Gemini API keys are exactly 39 characters long.\n"
            "   Get a key from: https://aistudio.google.com/app/apikey"
        )

    # Try to import and use the Gemini API
    try:
        import google.generativeai as genai
    except ImportError:
        return False, (
            "❌ google-generativeai package not installed.\n"
            "   Install with: pip install google-generativeai"
        )

    # Configure and test the API key
    try:
        genai.configure(api_key=api_key)

        # List available models to verify API key works
        models = genai.list_models()
        available_models = [
            m.name for m in models if "generateContent" in m.supported_generation_methods
        ]

        if not available_models:
            return False, (
                "❌ No models available with your API key.\n"
                "   The key may be valid but has no access to Gemini models.\n"
                "   Check your API key settings: https://aistudio.google.com/app/apikey"
            )

        # Use the first available model for a quick test
        model_name = available_models[0].replace("models/", "")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'OK'", generation_config={"max_output_tokens": 5})

        # If we got here, the key is valid
        return True, (
            f"✅ API key is valid!\n"
            f"   Key: {api_key[:10]}...{api_key[-4:]}\n"
            f"   Test response: {response.text.strip()}\n"
            f"   Model tested: {model_name}\n"
            f"   Available models: {len(available_models)}\n"
            f"   You're ready to use Gemini with CrewAI!"
        )

    except Exception as e:
        error_msg = str(e)

        # Parse common error messages
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
            return False, (
                f"❌ API key is invalid or expired.\n"
                f"   Key: {api_key[:10]}...{api_key[-4:]}\n"
                f"   Get a new key from: https://aistudio.google.com/app/apikey"
            )
        elif "quota" in error_msg.lower():
            return False, (
                "❌ API quota exceeded.\n"
                "   Your API key may be valid but you've hit rate limits.\n"
                "   Check your quota: https://aistudio.google.com/app/apikey"
            )
        elif "PERMISSION_DENIED" in error_msg:
            return False, (
                "❌ Permission denied.\n"
                "   The API key doesn't have permission to use Gemini.\n"
                "   Enable the API: https://aistudio.google.com/app/apikey"
            )
        else:
            return False, (
                f"❌ API request failed: {error_msg}\n"
                f"   Check your network connection and API key."
            )


def main():
    """Run the validation and print results."""
    print("🔍 Validating Gemini API Key...")
    print("=" * 60)

    is_valid, message = validate_gemini_key()
    print(message)
    print("=" * 60)

    if is_valid:
        print("\n✨ You can now run the Gemini research agent:")
        print('   python examples/crewai_gemini_research_agent.py "your topic"')
        sys.exit(0)
    else:
        print("\n💡 Next steps:")
        print("   1. Visit: https://aistudio.google.com/app/apikey")
        print("   2. Create or copy your API key")
        print("   3. Add it to your .env file:")
        print("      GOOGLE_API_KEY=your_key_here")
        sys.exit(1)


if __name__ == "__main__":
    main()
