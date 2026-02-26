"""FLUX API service for image generation using Black Forest Labs API."""
import requests, os
import time
from typing import Optional
from app.core.config import settings


def generate_image(
    prompt: str,
    material_image_url: str,
    previous_image_url: Optional[str] = None,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None,
    model_name: Optional[str] = None,
) -> Optional[str]:
    """
    Generate an image using FLUX 2 Image Editing API (Black Forest Labs).
    
    Supports two modes:
    1. Material-to-Image: Only material composition + prompt (initial generation)
    2. Iterative Editing: Previous image + material composition + prompt (refinement)
    
    Uses the official BFL API with polling for async generation.
    
    Args:
        prompt: The optimized prompt for FLUX describing what to build.
        material_image_url: URL of the material composition image (required).
                           This shows the materials that will be used.
        previous_image_url: Optional URL of a previous generation step.
                           If provided, FLUX will edit this image based on the prompt.
                           If None, generates from scratch using materials.
        width: Image width (default: 1024).
        height: Image height (default: 1024).
        seed: Optional seed for reproducible results.
        
    Returns:
        URL of the generated image, or None if generation fails.
    
    Example:
        # Step 1: Generate base from materials
        img1 = generate_image(
            prompt="Arrange two concrete blocks on a floor",
            material_image_url="https://materials.jpg"
        )
        
        # Step 2: Add to previous image
        img2 = generate_image(
            prompt="Add a steel pipe standing between the blocks",
            material_image_url="https://materials.jpg",
            previous_image_url=img1
        )
        
        # Step 3: Continue building
        img3 = generate_image(
            prompt="Add a wood plank on top of the pipe",
            material_image_url="https://materials.jpg",
            previous_image_url=img2
        )
    """
    if not prompt:
        print("â ï¸  No prompt provided")
        return None
    
    if not material_image_url:
        print("â ï¸  No material_image_url provided")
        return None
    
    if not settings.bfl_api_key:
        print("â ï¸  BFL_API_KEY not set")
        return None
    
    try:
        # FLUX 2 Image Editing endpoint
        api_url = f'https://api.bfl.ai/v1/{settings.flux_model}'
        
        # Determine generation mode
        if previous_image_url:
            print(f"ð Iterative mode: Editing previous image with materials")
            print(f"   Previous: {previous_image_url[:60]}...")
        else:
            print(f"ð¨ Initial mode: Generating from materials")
        
        print(f"ð¤ Submitting to {settings.flux_model}...")
        print(f"   Materials: {material_image_url[:60]}...")
        
        # Build request payload according to FLUX 2 Image Editing API
        request_json = {
            'prompt': prompt,
            'width': width,
            'height': height,
        }
        
        # FLUX 2 Image Editing uses input_image and input_image_2
        if previous_image_url:
            # Iterative mode: previous image + materials
            request_json['input_image'] = previous_image_url
            request_json['input_image_2'] = material_image_url
        else:
            # Initial mode: only materials
            request_json['input_image'] = material_image_url

        # Check if model name is specified
        if not model_name:
            model_name = settings.flux_model

        if model_name == "flux-2-flex":
            request_json['steps'] = 50  # More steps for higher quality
            request_json['guidance'] = 9.0  # Stronger adherence to prompt
        
        # Add optional seed
        if seed is not None:
            request_json['seed'] = seed
            print(f"ð² Using seed: {seed}")
        
        response = requests.post(
            api_url,
            headers={
                'accept': 'application/json',
                'x-key': settings.bfl_api_key,
                'Content-Type': 'application/json',
            },
            json=request_json
        )
        
        if response.status_code != 200:
            print(f"â FLUX API error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        request_id = data.get('id')
        polling_url = data.get('polling_url')
        
        if not request_id:
            print(f"â No request ID in response: {data}")
            return None
        
        # Use provided polling_url or construct default
        if not polling_url:
            polling_url = f'https://api.bfl.ai/v1/get_result?id={request_id}'
        
        print(f"â³ Request ID: {request_id}, polling for result...")
        
        # Poll for result (max 120 seconds for FLUX 2)
        max_attempts = 240  # 120 seconds with 0.5s intervals
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(0.5)
            attempt += 1
            
            result = requests.get(
                polling_url,
                headers={
                    'accept': 'application/json',
                    'x-key': settings.bfl_api_key,
                }
            ).json()
            
            status = result.get('status')
            
            if status == 'Ready':
                image_url = result.get('result', {}).get('sample')
                if image_url:
                    print(f"â FLUX image generated: {image_url}")
                    return image_url
                else:
                    print(f"â ï¸  No image URL in result: {result}")
                    return None
            
            elif status in ['Error', 'Failed']:
                error_msg = result.get('error', 'Unknown error')
                print(f"â Generation failed: {error_msg}")
                return None
            
            # Status is still 'Pending' or other, continue polling
            if attempt % 10 == 0:
                print(f"Still waiting... ({attempt * 0.5}s)")
        
        print(f"â° Timeout after {max_attempts * 0.5}s")
        return None
        
    except Exception as e:
        print(f"â FLUX generation error: {e}")
        import traceback
        traceback.print_exc()
        return None

