from flask import Flask, request, jsonify
import requests
import mimetypes
import io

# Vercel will look for the 'app' object
app = Flask(__name__)

# The file is at /api/enhance.py, so Vercel routes /api/enhance here.
# We define the route as '/' to match the file's root.
@app.route('/', methods=['POST'])
def enhance_image():
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image file provided."}), 400

    image = request.files['image']
    
    # Read image data into memory
    image_data = image.stream.read()
    image.stream.close() # Close original stream
    
    # Get mimetype
    mimetype = mimetypes.guess_type(image.filename)[0] or 'application/octet-stream'

    # 1. Upload the image file to envs.sh
    try:
        files = {'file': (image.filename, io.BytesIO(image_data), mimetype)}
        upload_response = requests.post('https://envs.sh', files=files)
        upload_response.raise_for_status()  # Check for HTTP errors
        
        hosted_image_url = upload_response.text.strip()
        
        if not hosted_image_url.startswith('http'):
            # envs.sh might return an error message
            raise Exception(f"File host did not return a valid URL. Response: {hosted_image_url}")

    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Failed to upload image to host: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"File hosting error: {str(e)}"}), 500

    # 2. Call the enhancement API with the hosted URL
    try:
        api_url = "https://myrestapi-xi.vercel.app/imagecreator/remini"
        params = {"url": hosted_image_url}
        
        # This API might take a while, set a reasonable timeout
        enhance_response = requests.get(api_url, params=params, timeout=60) # 60 sec timeout
        enhance_response.raise_for_status()
        
        enhance_data = enhance_response.json()

        if enhance_data.get("status") and "result" in enhance_data:
            result_url = enhance_data["result"]
            # 3. Return the final enhanced URL to the frontend
            return jsonify({"success": True, "enhanced_url": result_url})
        else:
            api_message = enhance_data.get("message", "Unknown API error")
            return jsonify({"success": False, "message": f"Enhancement API failed: {api_message}"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "The enhancement API timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Failed to call enhancement API: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing enhancement: {str(e)}"}), 500

# This allows Vercel to run the Flask app.
# When running locally for testing, you'd use `app.run()`
# But for Vercel, just providing the `app` object is correct.
