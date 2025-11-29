# Testing the FLUX Endpoint

## Endpoint

`POST /api/v1/test-flux`

## Example 1: Initial Generation (from materials only)

```bash
curl -X POST "http://localhost:8000/api/v1/test-flux" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Arrange two concrete blocks on a floor",
    "material_image_url": "https://example.com/materials.jpg",
    "width": 1024,
    "height": 1024
  }'
```

## Example 2: Iterative Editing (refining previous image)

```bash
curl -X POST "http://localhost:8000/api/v1/test-flux" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Add a steel pipe standing between the blocks",
    "material_image_url": "https://example.com/materials.jpg",
    "previous_image_url": "https://example.com/previous-generation.jpg",
    "width": 1024,
    "height": 1024
  }'
```

## Example 3: With Seed (reproducible results)

```bash
curl -X POST "http://localhost:8000/api/v1/test-flux" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Build a cyberpunk throne from metal and wood",
    "material_image_url": "https://example.com/materials.jpg",
    "width": 1024,
    "height": 1024,
    "seed": 42
  }'
```

## Response Format

Success:

```json
{
  "success": true,
  "image_url": "https://generated-image-url.jpg",
  "error": null
}
```

Failure:

```json
{
  "success": false,
  "image_url": null,
  "error": "Error message with details"
}
```

## Testing with Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/test-flux",
    json={
        "prompt": "Arrange two concrete blocks on a floor",
        "material_image_url": "https://example.com/materials.jpg",
        "width": 1024,
        "height": 1024
    }
)

result = response.json()
if result["success"]:
    print(f"Generated image: {result['image_url']}")
else:
    print(f"Error: {result['error']}")
```
