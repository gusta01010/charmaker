import requests
import io
import base64
import tempfile
import os
from PIL import Image
from urllib.parse import urlparse, parse_qs
import file_dialogs

class ImageHandler:
    """Handles image loading, processing, and validation"""
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
    MAX_SIZE_MB = 10
    
    @staticmethod
    def is_image_url(url):
        """Check if URL points to an image, handling complex URLs"""
        if not url.lower().startswith('http'):
            return False
            
        # Parse URL and check extension
        parsed = urlparse(url.lower())
        path = parsed.path
        
        # Direct extension check
        if any(path.endswith(ext) for ext in ImageHandler.SUPPORTED_FORMATS):
            return True
            
        # Check for image indicators in URL
        image_indicators = ['image', 'img', 'photo', 'pic', 'thumb']
        if any(indicator in url.lower() for indicator in image_indicators):
            return True
            
        # Check query parameters for image hints
        query_params = parse_qs(parsed.query)
        if 'f' in query_params or 'format' in query_params:
            return True
            
        return False
    
    @staticmethod
    def load_from_url(url, timeout=10):
        """Load image from URL with robust error handling"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=timeout)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"Warning: Content-Type is '{content_type}', not an image")
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > ImageHandler.MAX_SIZE_MB * 1024 * 1024:
                raise ValueError(f"Image too large: {int(content_length) / (1024*1024):.1f}MB")
            
            # Load and validate image
            image_data = response.content
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify it's a valid image
            
            # Reload for actual use (verify() closes the file)
            image = Image.open(io.BytesIO(image_data))
            print(f"✓ Image loaded: {image.size[0]}x{image.size[1]} {image.format}")
            return image
            
        except requests.RequestException as e:
            print(f"✗ Network error loading image: {e}")
        except Exception as e:
            print(f"✗ Error processing image: {e}")
        return None
    
    @staticmethod
    def load_from_file(filepath):
        """Load image from local file"""
        try:
            if not os.path.exists(filepath):
                print(f"✗ File not found: {filepath}")
                return None
                
            image = Image.open(filepath)
            print(f"✓ Image loaded: {image.size[0]}x{image.size[1]} {image.format}")
            return image
            
        except Exception as e:
            print(f"✗ Error opening image file: {e}")
            return None
    
    @staticmethod
    def load_image(source):
        """Universal image loader - handles URLs, file paths, or dialog"""
        if source == '!':
            filepath = file_dialogs.open_image_dialog()
            return ImageHandler.load_from_file(filepath) if filepath else None
        elif ImageHandler.is_image_url(source):
            return ImageHandler.load_from_url(source)
        elif os.path.exists(source):
            return ImageHandler.load_from_file(source)
        else:
            print(f"✗ Invalid image source: {source}")
            return None
    
    @staticmethod
    def to_base64(image, format='JPEG', quality=85):
        """Convert PIL image to base64 string"""
        try:
            # Convert RGBA/P to RGB for JPEG
            if format.upper() == 'JPEG' and image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            buffered = io.BytesIO()
            save_kwargs = {'format': format}
            if format.upper() == 'JPEG':
                save_kwargs['quality'] = quality
                
            image.save(buffered, **save_kwargs)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        except Exception as e:
            print(f"✗ Error converting image to base64: {e}")
            return None
    
    @staticmethod
    def save_temp_image(image_data, suffix='.png'):
        """Save image data to temporary file"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(image_data)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            print(f"✗ Error saving temp image: {e}")
            return None
    
    @staticmethod
    def cleanup_temp_file(filepath):
        """Clean up temporary file"""
        if filepath and filepath.startswith(tempfile.gettempdir()):
            try:
                os.unlink(filepath)
            except OSError:
                pass