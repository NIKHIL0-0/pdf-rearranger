#!/usr/bin/env python3
"""
Simple test to verify environment variables and Gemini API key are working
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_variables():
    """Test if environment variables are loaded correctly"""
    print("=== Environment Variables Test ===")
    
    # Test API key
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        # Mask the key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"✅ GEMINI_API_KEY loaded: {masked_key}")
        print(f"   Length: {len(api_key)} characters")
        print(f"   Type: {type(api_key)}")
    else:
        print("❌ GEMINI_API_KEY not found or empty")
        return False
    
    # Test other variables
    other_vars = ['USE_GEMINI_BY_DEFAULT', 'ENABLE_OCR_FALLBACK', 'DETECT_DUPLICATES', 'GENERATE_TOC']
    for var in other_vars:
        value = os.getenv(var, 'NOT_SET')
        print(f"   {var}: {value}")
    
    return True

def test_gemini_api():
    """Test if Gemini API key actually works"""
    print("\n=== Gemini API Test ===")
    
    try:
        import google.generativeai as genai
        print("✅ google-generativeai package imported successfully")
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ No API key available for testing")
            return False
        
        # Configure with API key
        genai.configure(api_key=api_key)
        print("✅ API key configured")
        
        # Simple test request - try multiple model names
        model_names = ['gemini-2.0-flash-exp', 'gemini-1.5-flash', 'gemini-pro']
        model = None
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"✅ Model initialized: {model_name}")
                break
            except Exception as e:
                print(f"   ⚠️  Failed {model_name}: {str(e)[:50]}...")
                continue
        
        if not model:
            print("❌ No working model found")
            return False
        
        # Test with a simple prompt
        response = model.generate_content("Say 'API key working' if you can read this")
        print(f"✅ API Response: {response.text.strip()}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ API error: {e}")
        return False

if __name__ == "__main__":
    print("PDF Rearranger - Environment & API Test")
    print("=" * 50)
    
    env_ok = test_env_variables()
    if env_ok:
        api_ok = test_gemini_api()
        
        if env_ok and api_ok:
            print("\n🎉 All tests passed! Environment and API key are working correctly.")
        else:
            print("\n⚠️  Environment loaded but API test failed.")
    else:
        print("\n❌ Environment variable test failed.")