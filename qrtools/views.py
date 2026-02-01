"""
QR Tools Views - Professional Implementation
Features: Dynamic QR, Analytics, Profile Cards, Bulk Generation
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import *
from qrcode.image.styles.colormasks import *
import cloudinary.uploader
from io import BytesIO
import base64
import zipfile
from PIL import Image, ImageDraw, ImageFont
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Import models AFTER all other imports
try:
    from .models import QRCode, ProfileCard, QRScan, BulkQRBatch, QRTemplate
except ImportError as e:
    logger.error(f"Failed to import models: {e}")
    # Define placeholder classes if import fails
    class QRCode:
        pass
    class ProfileCard:
        pass
    class QRScan:
        pass
    class BulkQRBatch:
        pass
    class QRTemplate:
        pass
import time

from functools import wraps
# ============================================
# UTILITY FUNCTIONS
# ============================================
def rate_limit(max_requests=10, window=60):
    """Simple rate limiting decorator"""
    requests = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request)
            now = time.time()
            
            # Clean old entries
            requests[ip] = [req_time for req_time in requests.get(ip, []) 
                           if now - req_time < window]
            
            # Check rate limit
            if len(requests.get(ip, [])) >= max_requests:
                return JsonResponse({
                    'error': f'Rate limit exceeded. Max {max_requests} requests per {window} seconds.'
                }, status=429)
            
            # Add current request
            requests.setdefault(ip, []).append(now)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple"""
    if not hex_color or not isinstance(hex_color, str):
        return (0, 0, 0)
    
    hex_color = hex_color.lstrip('#')
    
    if len(hex_color) == 3:
        # Expand shorthand (e.g., #FFF to #FFFFFF)
        hex_color = ''.join([c*2 for c in hex_color])
    
    if len(hex_color) != 6:
        return (0, 0, 0)
    
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (0, 0, 0)


def parse_color(color_value):
    """Parse color value which could be hex string, RGB tuple, or color name"""
    if isinstance(color_value, str):
        if color_value.startswith('#'):
            return hex_to_rgb(color_value)
        elif ',' in color_value:
            # Try to parse as comma-separated RGB
            try:
                parts = color_value.split(',')
                if len(parts) == 3:
                    return tuple(int(p.strip()) for p in parts)
            except:
                pass
        else:
            # Color names
            color_names = {
                'black': (0, 0, 0),
                'white': (255, 255, 255),
                'red': (255, 0, 0),
                'green': (0, 255, 0),
                'blue': (0, 0, 255),
                'yellow': (255, 255, 0),
                'purple': (128, 0, 128),
                'orange': (255, 165, 0),
                'gray': (128, 128, 128),
                'grey': (128, 128, 128),
            }
            if color_value.lower() in color_names:
                return color_names[color_value.lower()]
    
    elif isinstance(color_value, (tuple, list)) and len(color_value) in (3, 4):
        return tuple(int(c) for c in color_value[:3])
    
    return (0, 0, 0)


def create_styled_qr(data, config):
    """
    Create a professionally styled QR code with advanced features
    
    Features:
    - Multiple pattern styles (square, dots, rounded, etc.)
    - Gradient colors
    - Logo with padding and border
    - Decorative frames
    - Custom colors
    
    Args:
        data (str): Data to encode in QR code
        config (dict): Configuration dictionary with styling options
        
    Returns:
        PIL.Image: Generated QR code image
    """
    try:
        # ============================================
        # 1. SETUP & CONFIGURATION
        # ============================================
        
        # Error correction mapping
        error_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }
        
        # Pattern drawer mapping
        pattern_map = {
            'square': SquareModuleDrawer(),
            'dots': CircleModuleDrawer(),
            'rounded': RoundedModuleDrawer(),
            'classy': GappedSquareModuleDrawer(),
            'classy-rounded': VerticalBarsDrawer(),
            'extra-rounded': HorizontalBarsDrawer(),
            'fluid': CircleModuleDrawer(),
        }
        
        # Get configuration values
        pattern_style = config.get('pattern_style', 'square')
        primary_color_rgb = parse_color(config.get('primary_color', '#000000'))
        background_color_rgb = parse_color(config.get('background_color', '#FFFFFF'))
        
        # ============================================
        # 2. CREATE QR CODE
        # ============================================
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_map.get(config.get('error_correction', 'M'), qrcode.constants.ERROR_CORRECT_M),
            box_size=config.get('box_size', 10),
            border=config.get('border', 4),
        )
        
        qr.add_data(data)
        
        # Try to make QR code
        try:
            qr.make(fit=True)
        except Exception as e:
            logger.warning(f"QR make failed, trying with larger version: {e}")
            # Try with smaller data or larger version
            qr = qrcode.QRCode(
                version=10,
                error_correction=error_map.get(config.get('error_correction', 'M'), qrcode.constants.ERROR_CORRECT_M),
                box_size=8,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=False)
        
        # ============================================
        # 3. APPLY COLORS & GRADIENTS
        # ============================================
        
        # Create color mask
        if config.get('gradient_enabled') and config.get('gradient_color'):
            gradient_color_rgb = parse_color(config.get('gradient_color'))
            
            if config.get('gradient_type') == 'radial':
                color_mask = RadialGradiantColorMask(
                    center_color=primary_color_rgb,
                    edge_color=gradient_color_rgb
                )
            else:
                color_mask = SquareGradiantColorMask(
                    back_color=background_color_rgb,
                    center_color=primary_color_rgb,
                    edge_color=gradient_color_rgb
                )
        else:
            color_mask = SolidFillColorMask(
                front_color=primary_color_rgb,
                back_color=background_color_rgb
            )
        
        # ============================================
        # 4. GENERATE IMAGE WITH PATTERN
        # ============================================
        
        # Get module drawer - use square as fallback for any errors
        module_drawer = pattern_map.get(pattern_style, SquareModuleDrawer())
        
        # Generate image with try-catch for module drawer errors
        try:
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=module_drawer,
                color_mask=color_mask,
                embeded_image_path=None
            )
        except Exception as e:
            logger.warning(f"Module drawer {pattern_style} failed, using square: {e}")
            # Fallback to square drawer
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=SquareModuleDrawer(),
                color_mask=color_mask,
                embeded_image_path=None
            )
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # ============================================
        # 5. ADD LOGO WITH PADDING (IF SPECIFIED)
        # ============================================
        
        if config.get('has_logo') and (config.get('logo_url') or config.get('logo_base64')):
            try:
                logo = None
                
                # Handle base64 logo
                if config.get('logo_is_base64'):
                    # Decode base64
                    if config.get('logo_url', '').startswith('data:image'):
                        # Data URL format: data:image/png;base64,...
                        base64_data = config['logo_url'].split(',')[1]
                    else:
                        # Plain base64
                        base64_data = config['logo_url']
                    
                    logo_data = base64.b64decode(base64_data)
                    logo = Image.open(BytesIO(logo_data))
                
                # Handle URL logo
                elif config.get('logo_url'):
                    response = requests.get(config['logo_url'], timeout=5)
                    logo = Image.open(BytesIO(response.content))
                
                if logo:
                    # Calculate logo size
                    qr_width, qr_height = img.size
                    logo_size_percent = config.get('logo_size', 20)
                    logo_max_size = int(qr_width * logo_size_percent / 100)
                    
                    # Ensure minimum size
                    logo_max_size = max(logo_max_size, 20)
                    
                    # Resize logo maintaining aspect ratio
                    logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
                    
                    # Make circular or rounded if specified
                    logo_shape = config.get('logo_shape', 'square')
                    
                    if logo_shape == 'circle':
                        mask = Image.new('L', logo.size, 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0) + logo.size, fill=255)
                        logo.putalpha(mask)
                    elif logo_shape == 'rounded':
                        mask = Image.new('L', logo.size, 0)
                        draw = ImageDraw.Draw(mask)
                        radius = min(logo.size) // 8
                        draw.rounded_rectangle([(0, 0) + logo.size], radius=radius, fill=255)
                        logo.putalpha(mask)
                    
                    # ═══════════════════════════════════════════
                    # ADD PADDING/SPACING AROUND LOGO
                    # ═══════════════════════════════════════════
                    
                    # Default 30% padding (adds ~15% on each side)
                    logo_padding_percent = config.get('logo_padding', 30)
                    padding_size = int(logo.size[0] * logo_padding_percent / 100)
                    logo_with_padding_size = logo.size[0] + padding_size
                    
                    # Create background with padding
                    logo_bg = Image.new('RGBA', (logo_with_padding_size, logo_with_padding_size), 
                                      (*background_color_rgb, 255))
                    
                    # Add border (optional, controlled by config)
                    add_border = config.get('logo_border', True)
                    if add_border:
                        draw = ImageDraw.Draw(logo_bg)
                        border_width = max(2, padding_size // 8)
                        
                        if logo_shape == 'circle':
                            # Draw white circle background
                            draw.ellipse([(0, 0), (logo_with_padding_size, logo_with_padding_size)],
                                       fill=(*background_color_rgb, 255))
                            # Add colored border
                            draw.ellipse([(border_width, border_width), 
                                        (logo_with_padding_size - border_width, 
                                         logo_with_padding_size - border_width)],
                                       outline=(*primary_color_rgb, 255), width=border_width)
                        
                        elif logo_shape == 'rounded':
                            # Draw rounded rectangle background
                            radius = logo_with_padding_size // 8
                            draw.rounded_rectangle([(0, 0), (logo_with_padding_size, logo_with_padding_size)],
                                                 radius=radius, fill=(*background_color_rgb, 255))
                            # Add border
                            draw.rounded_rectangle([(border_width, border_width),
                                                  (logo_with_padding_size - border_width,
                                                   logo_with_padding_size - border_width)],
                                                 radius=radius, outline=(*primary_color_rgb, 255), 
                                                 width=border_width)
                        
                        else:  # square
                            # Square background (already created)
                            # Just add border
                            draw.rectangle([(border_width, border_width),
                                          (logo_with_padding_size - border_width,
                                           logo_with_padding_size - border_width)],
                                         outline=(*primary_color_rgb, 255), width=border_width)
                    
                    # Paste logo on padded background (centered)
                    logo_paste_pos = (padding_size // 2, padding_size // 2)
                    logo_bg.paste(logo, logo_paste_pos, logo if logo.mode == 'RGBA' else None)
                    
                    # Update logo to be the version with padding
                    logo = logo_bg
                    
                    # ═══════════════════════════════════════════
                    # END PADDING SECTION
                    # ═══════════════════════════════════════════
                    
                    # Paste logo on QR code (centered)
                    logo_pos = ((qr_width - logo.size[0]) // 2, (qr_height - logo.size[1]) // 2)
                    img.paste(logo, logo_pos, logo if logo.mode == 'RGBA' else None)
                    
            except Exception as e:
                logger.warning(f"Failed to add logo: {e}")
        
        # ============================================
        # 6. ADD DECORATIVE FRAME (IF SPECIFIED)
        # ============================================
        
        frame_style = config.get('frame_style', 'none')
        if frame_style and frame_style != 'none':
            img = add_frame_safe(img, frame_style, primary_color_rgb)
        
        # ============================================
        # 7. RESIZE TO REQUESTED SIZE
        # ============================================
        
        requested_size = config.get('size', 300)
        if img.size[0] != requested_size or img.size[1] != requested_size:
            img = img.resize((requested_size, requested_size), Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        logger.error(f"Error in create_styled_qr: {e}", exc_info=True)
        
        # ============================================
        # FALLBACK: CREATE SIMPLE QR CODE
        # ============================================
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            # Use simple black and white colors for fallback
            img = qr.make_image(fill_color=(0, 0, 0), back_color=(255, 255, 255)).convert('RGB')
            # Resize to requested size
            requested_size = config.get('size', 300)
            img = img.resize((requested_size, requested_size), Image.Resampling.LANCZOS)
            return img
        except:
            # Ultimate fallback - blank white image
            return Image.new('RGB', (config.get('size', 300), config.get('size', 300)), (255, 255, 255))


def add_frame_safe(img, frame_style, color_rgb):
    """
    Add decorative frame to QR code
    
    Available frame styles:
    - square: Simple square border
    - rounded: Rounded corner border
    - circle: Circular border
    - scan-me: Square border with "SCAN ME" text
    - badge: Square with corner accents
    - modern: Double border frame
    - vintage: Dotted/dashed vintage style
    - neon: Glowing neon effect
    - minimal: Corner-only accents
    
    Args:
        img (PIL.Image): QR code image
        frame_style (str): Frame style to apply
        color_rgb (tuple): RGB color for frame (r, g, b)
        
    Returns:
        PIL.Image: QR code with frame
    """
    try:
        if frame_style == 'none' or not frame_style:
            return img
        
        # Ensure color_rgb is a valid tuple and extract only RGB (no alpha)
        if not isinstance(color_rgb, (tuple, list)) or len(color_rgb) not in (3, 4):
            color_rgb = (0, 0, 0)  # Default to black
        else:
            # Force to 3-tuple RGB, convert to int
            color_rgb = tuple(int(c) for c in color_rgb[:3])
        
        # Get original image size
        width, height = img.size
        
        # Ensure image is square (QR codes should be square)
        if width != height:
            # Make it square by taking the minimum dimension
            size = min(width, height)
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            width = height = size
        
        # Convert image to RGB if it's not already
        if img.mode not in ['RGB', 'RGBA']:
            img = img.convert('RGB')
        
        # Define padding based on image size
        padding = max(20, min(width, height) // 10)
        
        # Create new image with padding
        new_width = width + padding * 2
        new_height = height + padding * 2
        
        # Add extra space for text if needed
        if frame_style == 'scan-me':
            new_height += 40
        
        # Create new image for the frame - use RGB mode
        framed = Image.new('RGB', (new_width, new_height), (255, 255, 255))
        
        # Paste original image
        try:
            # Convert to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', (width, height), (255, 255, 255))
                background.paste(img, (0, 0), mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to exact dimensions
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Paste using 4-tuple box
            framed.paste(img, (padding, padding, padding + width, padding + height))

        except Exception as e:
            logger.error(f"Failed to paste image: {e}", exc_info=True)
            return img
        
        draw = ImageDraw.Draw(framed)
        
        # Calculate frame coordinates
        left = padding
        top = padding
        right = padding + width
        bottom = padding + height
        
        # Adjust frame to be slightly larger than QR code
        frame_left = max(5, left - 5)
        frame_top = max(5, top - 5)
        frame_right = min(new_width - 5, right + 5)
        frame_bottom = min(new_height - 5, bottom + 5)
        
        # Ensure valid coordinates
        if frame_right <= frame_left:
            frame_right = frame_left + 10
        if frame_bottom <= frame_top:
            frame_bottom = frame_top + 10
        
        # ============================================
        # DRAW FRAME BASED ON STYLE
        # ============================================
        
        if frame_style == 'square':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        elif frame_style == 'rounded':
            try:
                if hasattr(draw, 'rounded_rectangle'):
                    draw.rounded_rectangle(
                        [frame_left, frame_top, frame_right, frame_bottom],
                        radius=15,
                        outline=color_rgb,
                        width=3
                    )
                else:
                    draw.rectangle(
                        [(frame_left, frame_top), (frame_right, frame_bottom)],
                        outline=color_rgb,
                        width=3
                    )
            except Exception as e:
                logger.warning(f"Rounded rectangle failed: {e}")
                draw.rectangle(
                    [(frame_left, frame_top), (frame_right, frame_bottom)],
                    outline=color_rgb,
                    width=3
                )
        
        elif frame_style == 'scan-me':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
            try:
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    try:
                        font = ImageFont.truetype("DejaVuSans.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                
                text = "SCAN ME"
                try:
                    text_bbox = draw.textbbox((0, 0), text, font=font)
                except:
                    text_bbox = draw.textsize(text, font=font)
                    text_bbox = (0, 0, text_bbox[0], text_bbox[1])
                
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (new_width - text_width) // 2
                text_y = new_height - text_height - 10
                draw.text((text_x, text_y), text, fill=color_rgb, font=font)
            except Exception as e:
                logger.warning(f"Text drawing failed: {e}")
        
        elif frame_style == 'circle':
            center_x = new_width // 2
            center_y = new_height // 2
            radius = min(width, height) // 2 + 5
            
            if radius > 0:
                draw.ellipse(
                    [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
                    outline=color_rgb,
                    width=3
                )
            else:
                draw.rectangle(
                    [(frame_left, frame_top), (frame_right, frame_bottom)],
                    outline=color_rgb,
                    width=3
                )
        
        elif frame_style == 'badge':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
            corner_length = 20
            # Top-left corner
            draw.line([(frame_left, frame_top + corner_length), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_top), (frame_left, frame_top)], fill=color_rgb, width=2)
            # Top-right corner
            draw.line([(frame_right - corner_length, frame_top), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_top + corner_length), (frame_right, frame_top)], fill=color_rgb, width=2)
            # Bottom-left corner
            draw.line([(frame_left, frame_bottom - corner_length), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_bottom), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            # Bottom-right corner
            draw.line([(frame_right - corner_length, frame_bottom), (frame_right, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_bottom - corner_length), (frame_right, frame_bottom)], fill=color_rgb, width=2)
        
        elif frame_style == 'modern':
            # Outer border
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=4
            )
            # Inner border
            inner_left = frame_left + 8
            inner_top = frame_top + 8
            inner_right = frame_right - 8
            inner_bottom = frame_bottom - 8
            
            if inner_right > inner_left and inner_bottom > inner_top:
                draw.rectangle(
                    [(inner_left, inner_top), (inner_right, inner_bottom)],
                    outline=color_rgb,
                    width=2
                )
        
        elif frame_style == 'vintage':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=2
            )
            # Dotted lines on all sides
            dot_spacing = 8
            # Top
            for x in range(frame_left + dot_spacing, frame_right, dot_spacing * 2):
                if x + dot_spacing <= frame_right:
                    draw.line([(x, frame_top + 4), (x + dot_spacing, frame_top + 4)], fill=color_rgb, width=2)
            # Bottom
            for x in range(frame_left + dot_spacing, frame_right, dot_spacing * 2):
                if x + dot_spacing <= frame_right:
                    draw.line([(x, frame_bottom - 4), (x + dot_spacing, frame_bottom - 4)], fill=color_rgb, width=2)
            # Left
            for y in range(frame_top + dot_spacing, frame_bottom, dot_spacing * 2):
                if y + dot_spacing <= frame_bottom:
                    draw.line([(frame_left + 4, y), (frame_left + 4, y + dot_spacing)], fill=color_rgb, width=2)
            # Right
            for y in range(frame_top + dot_spacing, frame_bottom, dot_spacing * 2):
                if y + dot_spacing <= frame_bottom:
                    draw.line([(frame_right - 4, y), (frame_right - 4, y + dot_spacing)], fill=color_rgb, width=2)
        
        elif frame_style == 'neon':
            # Glow effect (multiple outlines)
            for offset in [3, 2, 1]:
                glow_color = (
                    min(255, color_rgb[0] + 50),
                    min(255, color_rgb[1] + 50),
                    min(255, color_rgb[2] + 50)
                )
                glow_left = max(0, frame_left - offset)
                glow_top = max(0, frame_top - offset)
                glow_right = min(new_width - 1, frame_right + offset)
                glow_bottom = min(new_height - 1, frame_bottom + offset)
                
                if glow_right > glow_left and glow_bottom > glow_top:
                    draw.rectangle(
                        [(glow_left, glow_top), (glow_right, glow_bottom)],
                        outline=glow_color,
                        width=1
                    )
            # Main border
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        elif frame_style == 'minimal':
            # Corner accents only
            corner_length = 15
            # Top-left
            draw.line([(frame_left, frame_top + corner_length), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_top), (frame_left, frame_top)], fill=color_rgb, width=2)
            # Top-right
            draw.line([(frame_right - corner_length, frame_top), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_top + corner_length), (frame_right, frame_top)], fill=color_rgb, width=2)
            # Bottom-left
            draw.line([(frame_left, frame_bottom - corner_length), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_bottom), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            # Bottom-right
            draw.line([(frame_right - corner_length, frame_bottom), (frame_right, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_bottom - corner_length), (frame_right, frame_bottom)], fill=color_rgb, width=2)
        
        else:
            # Default: simple rectangle
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        return framed
        
    except Exception as e:
        logger.error(f"Error in add_frame_safe: {e}", exc_info=True)
        return img


def add_frame_safe(img, frame_style, color_rgb):
    """Safe version to add decorative frame to QR code"""
    try:
        if frame_style == 'none' or not frame_style:
            return img
        
        # Ensure color_rgb is a valid tuple and extract only RGB (no alpha)
        if not isinstance(color_rgb, (tuple, list)) or len(color_rgb) not in (3, 4):
            color_rgb = (0, 0, 0)  # Default to black
        else:
            # Force to 3-tuple RGB, convert to int
            color_rgb = tuple(int(c) for c in color_rgb[:3])
        
        # Get original image size
        width, height = img.size
        
        # Ensure image is square (QR codes should be square)
        if width != height:
            # Make it square by taking the minimum dimension
            size = min(width, height)
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            width = height = size
        
        # Convert image to RGB if it's not already
        if img.mode not in ['RGB', 'RGBA']:
            img = img.convert('RGB')
        
        # Define padding based on image size
        padding = max(20, min(width, height) // 10)
        
        # Create new image with padding
        new_width = width + padding * 2
        new_height = height + padding * 2
        
        # Add extra space for text if needed
        if frame_style == 'scan-me':
            new_height += 40
        
        # Create new image for the frame - use RGB mode
        framed = Image.new('RGB', (new_width, new_height), (255, 255, 255))
        
        # Paste original image - SIMPLEST WORKING METHOD
        try:
            # Convert to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', (width, height), (255, 255, 255))
                background.paste(img, (0, 0), mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to exact dimensions
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Use the 4-tuple box that PIL wants
            framed.paste(img, (padding, padding, padding + width, padding + height))

        except Exception as e:
            logger.error(f"Failed to paste image: {e}", exc_info=True)
            return img
        
        draw = ImageDraw.Draw(framed)
        
        # Calculate frame coordinates (around the QR code)
        left = padding
        top = padding
        right = padding + width
        bottom = padding + height
        
        # Adjust frame to be slightly larger than QR code
        frame_left = max(5, left - 5)
        frame_top = max(5, top - 5)
        frame_right = min(new_width - 5, right + 5)
        frame_bottom = min(new_height - 5, bottom + 5)
        
        # Ensure valid coordinates
        if frame_right <= frame_left:
            frame_right = frame_left + 10
        if frame_bottom <= frame_top:
            frame_bottom = frame_top + 10
        
        # Draw frame based on style
        if frame_style == 'square':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        elif frame_style == 'rounded':
            try:
                if hasattr(draw, 'rounded_rectangle'):
                    draw.rounded_rectangle(
                        [frame_left, frame_top, frame_right, frame_bottom],
                        radius=15,
                        outline=color_rgb,
                        width=3
                    )
                else:
                    draw.rectangle(
                        [(frame_left, frame_top), (frame_right, frame_bottom)],
                        outline=color_rgb,
                        width=3
                    )
            except Exception as e:
                logger.warning(f"Rounded rectangle failed: {e}")
                draw.rectangle(
                    [(frame_left, frame_top), (frame_right, frame_bottom)],
                    outline=color_rgb,
                    width=3
                )
        
        elif frame_style == 'scan-me':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
            try:
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    try:
                        font = ImageFont.truetype("DejaVuSans.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                
                text = "SCAN ME"
                try:
                    text_bbox = draw.textbbox((0, 0), text, font=font)
                except:
                    text_bbox = draw.textsize(text, font=font)
                    text_bbox = (0, 0, text_bbox[0], text_bbox[1])
                
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (new_width - text_width) // 2
                text_y = new_height - text_height - 10
                draw.text((text_x, text_y), text, fill=color_rgb, font=font)
            except Exception as e:
                logger.warning(f"Text drawing failed: {e}")
        
        elif frame_style == 'circle':
            center_x = new_width // 2
            center_y = new_height // 2
            radius = min(width, height) // 2 + 5
            
            if radius > 0:
                draw.ellipse(
                    [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
                    outline=color_rgb,
                    width=3
                )
            else:
                draw.rectangle(
                    [(frame_left, frame_top), (frame_right, frame_bottom)],
                    outline=color_rgb,
                    width=3
                )
        
        elif frame_style == 'badge':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
            corner_length = 20
            draw.line([(frame_left, frame_top + corner_length), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_top), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right - corner_length, frame_top), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_top + corner_length), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left, frame_bottom - corner_length), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_bottom), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right - corner_length, frame_bottom), (frame_right, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_bottom - corner_length), (frame_right, frame_bottom)], fill=color_rgb, width=2)
        
        elif frame_style == 'modern':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=4
            )
            inner_left = frame_left + 8
            inner_top = frame_top + 8
            inner_right = frame_right - 8
            inner_bottom = frame_bottom - 8
            
            if inner_right > inner_left and inner_bottom > inner_top:
                draw.rectangle(
                    [(inner_left, inner_top), (inner_right, inner_bottom)],
                    outline=color_rgb,
                    width=2
                )
        
        elif frame_style == 'vintage':
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=2
            )
            dot_spacing = 8
            for x in range(frame_left + dot_spacing, frame_right, dot_spacing * 2):
                if x + dot_spacing <= frame_right:
                    draw.line([(x, frame_top + 4), (x + dot_spacing, frame_top + 4)], fill=color_rgb, width=2)
            for x in range(frame_left + dot_spacing, frame_right, dot_spacing * 2):
                if x + dot_spacing <= frame_right:
                    draw.line([(x, frame_bottom - 4), (x + dot_spacing, frame_bottom - 4)], fill=color_rgb, width=2)
            for y in range(frame_top + dot_spacing, frame_bottom, dot_spacing * 2):
                if y + dot_spacing <= frame_bottom:
                    draw.line([(frame_left + 4, y), (frame_left + 4, y + dot_spacing)], fill=color_rgb, width=2)
            for y in range(frame_top + dot_spacing, frame_bottom, dot_spacing * 2):
                if y + dot_spacing <= frame_bottom:
                    draw.line([(frame_right - 4, y), (frame_right - 4, y + dot_spacing)], fill=color_rgb, width=2)
        
        elif frame_style == 'neon':
            for offset in [3, 2, 1]:
                glow_color = (
                    min(255, color_rgb[0] + 50),
                    min(255, color_rgb[1] + 50),
                    min(255, color_rgb[2] + 50)
                )
                glow_left = max(0, frame_left - offset)
                glow_top = max(0, frame_top - offset)
                glow_right = min(new_width - 1, frame_right + offset)
                glow_bottom = min(new_height - 1, frame_bottom + offset)
                
                if glow_right > glow_left and glow_bottom > glow_top:
                    draw.rectangle(
                        [(glow_left, glow_top), (glow_right, glow_bottom)],
                        outline=glow_color,
                        width=1
                    )
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        elif frame_style == 'minimal':
            corner_length = 15
            draw.line([(frame_left, frame_top + corner_length), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_top), (frame_left, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right - corner_length, frame_top), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_top + corner_length), (frame_right, frame_top)], fill=color_rgb, width=2)
            draw.line([(frame_left, frame_bottom - corner_length), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_left + corner_length, frame_bottom), (frame_left, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right - corner_length, frame_bottom), (frame_right, frame_bottom)], fill=color_rgb, width=2)
            draw.line([(frame_right, frame_bottom - corner_length), (frame_right, frame_bottom)], fill=color_rgb, width=2)
        
        else:
            draw.rectangle(
                [(frame_left, frame_top), (frame_right, frame_bottom)],
                outline=color_rgb,
                width=3
            )
        
        return framed
        
    except Exception as e:
        logger.error(f"Error in add_frame_safe: {e}", exc_info=True)
        return img
# ============================================
# ANALYTICS HELPER FUNCTIONS
# ============================================

def get_user_agent_info(request):
    """Parse user agent for device and browser info"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Simple device detection
    device_type = 'desktop'
    if 'mobile' in user_agent.lower():
        device_type = 'mobile'
    elif 'tablet' in user_agent.lower():
        device_type = 'tablet'
    
    # Simple browser detection
    browser = 'unknown'
    if 'chrome' in user_agent.lower():
        browser = 'chrome'
    elif 'firefox' in user_agent.lower():
        browser = 'firefox'
    elif 'safari' in user_agent.lower() and 'chrome' not in user_agent.lower():
        browser = 'safari'
    elif 'edge' in user_agent.lower():
        browser = 'edge'
    elif 'opera' in user_agent.lower():
        browser = 'opera'
    
    return {
        'device_type': device_type,
        'browser': browser,
        'user_agent': user_agent[:500]
    }

def get_location_info(request, ip_address):
    """Get location information from IP address"""
    try:
        # You can use a free service like ipinfo.io or ip-api.com
        # Note: For production, consider using a paid service or self-hosted solution
        if ip_address and ip_address != '127.0.0.1':
            # Free tier of ipinfo.io (50k requests/month)
            response = requests.get(f'https://ipinfo.io/{ip_address}/json', timeout=2)
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'latitude': data.get('loc', '0,0').split(',')[0],
                    'longitude': data.get('loc', '0,0').split(',')[1],
                }
    except Exception as e:
        logger.warning(f"Location lookup failed for IP {ip_address}: {e}")
    
    return {
        'country': 'Unknown',
        'region': 'Unknown',
        'city': 'Unknown',
        'latitude': '0',
        'longitude': '0',
    }

# ============================================
# MAIN VIEWS
# ============================================

@ensure_csrf_cookie
def qr_main_view(request):
    """Main QR tools page - Generator & Scanner"""
    
    # Get popular templates
    templates = QRTemplate.objects.filter(is_active=True).order_by('-usage_count')[:12]
    
    context = {
        'page_title': 'Professional QR Code Generator & Scanner - 21K Tools',
        'meta_description': 'Create stunning custom QR codes with logos, frames, gradients. Generate dynamic QR codes, profile cards, bulk QR codes. Advanced analytics included.',
        'meta_keywords': 'qr code generator, custom qr code, dynamic qr code, qr analytics, profile card qr, bulk qr generator',
        'templates': templates,
    }
    return render(request, 'qrtools/qr_main.html', context)


@require_http_methods(["POST"])
def generate_qr_api(request):
    """
    API endpoint to generate QR code
    Supports all QR types with advanced customization
    """
    try:
        data = json.loads(request.body)
        
        qr_type = data.get('qr_type', 'url')
        content_data = data.get('content_data', {})
        design_config = data.get('design_config', {})
        
        # Build QR data based on type
        qr_data = build_qr_data(qr_type, content_data)
        
        if not qr_data:
            return JsonResponse({'error': 'Invalid QR data'}, status=400)
        
        # Add box_size and border parameters
        size = design_config.get('size', 300)
        design_config['box_size'] = max(5, size // 30)
        design_config['border'] = 4
        
        # Create QR code in database
        qr_code = QRCode.objects.create(
            qr_type=qr_type,
            content_data=content_data,
            final_url=qr_data,
            is_dynamic=design_config.get('is_dynamic', True),
            primary_color=design_config.get('primary_color', '#000000'),
            background_color=design_config.get('background_color', '#FFFFFF'),
            gradient_enabled=design_config.get('gradient_enabled', False),
            gradient_color=design_config.get('gradient_color', ''),
            gradient_type=design_config.get('gradient_type', 'linear'),
            frame_style=design_config.get('frame_style', 'none'),
            pattern_style=design_config.get('pattern_style', 'square'),
            eye_style='square',
            has_logo=design_config.get('has_logo', False),
            logo_url=design_config.get('logo_url', ''),
            logo_shape=design_config.get('logo_shape', 'square'),
            logo_size=design_config.get('logo_size', 20),
            size=size,
            error_correction=design_config.get('error_correction', 'M'),
            title=design_config.get('title', ''),
            description=design_config.get('description', ''),
            folder_name=design_config.get('folder_name', ''),
            tags=design_config.get('tags', [])
        )
        
        # Generate QR image
        if qr_code.is_dynamic:
            # Use redirect URL for tracking
            actual_data = request.build_absolute_uri(qr_code.get_redirect_url())
            qr_code.redirect_url = qr_data
        else:
            actual_data = qr_data
        
        # Create styled QR code
        img = create_styled_qr(actual_data, design_config)
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG', quality=95)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        qr_code.qr_image = f'data:image/png;base64,{img_str}'
        
        # Optionally upload to Cloudinary
        if design_config.get('save_to_cloud', False):
            try:
                buffer.seek(0)
                upload_result = cloudinary.uploader.upload(
                    buffer,
                    folder='21k_qr_codes',
                    public_id=str(qr_code.unique_id),
                    format='png'
                )
                qr_code.qr_image_url = upload_result.get('secure_url')
            except Exception as e:
                logger.warning(f"Cloudinary upload failed: {e}")
        
        qr_code.save()
        
        return JsonResponse({
            'success': True,
            'qr_code': {
                'analytics_code': qr_code.analytics_code,
                'qr_image': qr_code.qr_image,
                'qr_image_url': qr_code.qr_image_url,
                'analytics_url': request.build_absolute_uri(qr_code.get_analytics_url()),
                'created_at': qr_code.created_at.isoformat(),
            }
        })
        
    except Exception as e:
        logger.error(f"QR generation error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def build_qr_data(qr_type, content_data):
    """Build QR data string based on type"""
    
    if qr_type == 'url':
        return content_data.get('url', '')
    
    elif qr_type == 'vcard':
        # Build vCard format
        vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{content_data.get('name', '')}
TEL:{content_data.get('phone', '')}
EMAIL:{content_data.get('email', '')}
ORG:{content_data.get('company', '')}
TITLE:{content_data.get('title', '')}
URL:{content_data.get('website', '')}
ADR:{content_data.get('address', '')}
END:VCARD"""
        return vcard.strip()
    
    elif qr_type == 'email':
        email = content_data.get('email', '')
        subject = content_data.get('subject', '')
        body = content_data.get('body', '')
        return f"mailto:{email}?subject={subject}&body={body}"
    
    elif qr_type == 'sms':
        phone = content_data.get('phone', '')
        message = content_data.get('message', '')
        return f"sms:{phone}?body={message}"
    
    elif qr_type == 'phone':
        return f"tel:{content_data.get('phone', '')}"
    
    elif qr_type == 'wifi':
        ssid = content_data.get('ssid', '')
        password = content_data.get('password', '')
        encryption = content_data.get('encryption', 'WPA')
        hidden = 'true' if content_data.get('hidden', False) else 'false'
        return f"WIFI:T:{encryption};S:{ssid};P:{password};H:{hidden};;"
    
    elif qr_type == 'upi':
        upi_id = content_data.get('upi_id', '')
        name = content_data.get('name', '')
        amount = content_data.get('amount', '')
        note = content_data.get('note', '')
        return f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}"
    
    elif qr_type == 'location':
        lat = content_data.get('latitude', '0')
        lng = content_data.get('longitude', '0')
        return f"geo:{lat},{lng}"
    
    elif qr_type == 'text':
        return content_data.get('text', '')
    
    elif qr_type == 'whatsapp':
        phone = content_data.get('phone', '').replace('+', '').replace(' ', '')
        message = content_data.get('message', '')
        if message:
            return f"https://wa.me/{phone}?text={message}"
        else:
            return f"https://wa.me/{phone}"
    
    elif qr_type == 'profile':
        return content_data.get('profile_url', '')
    
    return ''


@require_http_methods(["POST"])
def create_profile_card_api(request):
    """Create a custom profile card with QR code"""
    try:
        data = json.loads(request.body)
        
        profile_data = data.get('profile_data', {})
        design_config = data.get('design_config', {})
        
        # Add box_size and border parameters
        size = design_config.get('size', 400)
        design_config['box_size'] = max(5, size // 30)
        design_config['border'] = 4
        
        # Create QR code
        qr_code = QRCode.objects.create(
            qr_type='profile',
            is_dynamic=True,
            primary_color=design_config.get('primary_color', '#000000'),
            background_color=design_config.get('background_color', '#FFFFFF'),
            gradient_enabled=design_config.get('gradient_enabled', False),
            gradient_color=design_config.get('gradient_color', ''),
            frame_style=design_config.get('frame_style', 'none'),
            pattern_style=design_config.get('pattern_style', 'square'),
            eye_style='square',
            has_logo=design_config.get('has_logo', False),
            logo_url=design_config.get('logo_url', ''),
            logo_shape=design_config.get('logo_shape', 'square'),
            logo_size=design_config.get('logo_size', 20),
            title=design_config.get('title', '')
        )
        
        # Create profile card
        profile_card = ProfileCard.objects.create(
            qr_code=qr_code,
            full_name=profile_data.get('full_name', ''),
            title=profile_data.get('title', ''),
            company=profile_data.get('company', ''),
            tagline=profile_data.get('tagline', ''),
            email=profile_data.get('email', ''),
            phone=profile_data.get('phone', ''),
            whatsapp=profile_data.get('whatsapp', ''),
            website=profile_data.get('website', ''),
            linkedin=profile_data.get('linkedin', ''),
            twitter=profile_data.get('twitter', ''),
            instagram=profile_data.get('instagram', ''),
            github=profile_data.get('github', ''),
            profile_photo=profile_data.get('profile_photo', ''),
            bio=profile_data.get('bio', ''),
            theme_color=profile_data.get('theme_color', '#667eea'),
            layout_style=profile_data.get('layout_style', 'modern'),
        )
        
        # Generate QR with profile URL
        profile_url = request.build_absolute_uri(profile_card.get_absolute_url())
        qr_code.redirect_url = profile_url
        qr_code.final_url = profile_url
        
        # Create QR image
        actual_data = request.build_absolute_uri(qr_code.get_redirect_url())
        img = create_styled_qr(actual_data, design_config)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG', quality=95)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        qr_code.qr_image = f'data:image/png;base64,{img_str}'
        qr_code.save()
        
        return JsonResponse({
            'success': True,
            'analytics_code': qr_code.analytics_code,
            'profile_url': profile_url,
            'qr_image': qr_code.qr_image,
            'analytics_url': request.build_absolute_uri(qr_code.get_analytics_url()),
        })
        
    except Exception as e:
        logger.error(f"Profile card creation error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
def qr_redirect(request, code):
    """Redirect handler for dynamic QR codes with FULL analytics tracking"""
    
    qr_code = get_object_or_404(QRCode, analytics_code=code, is_active=True)
    
    # Get client information
    ip_address = get_client_ip(request)
    user_agent_info = get_user_agent_info(request)
    
    # Get location info (you might need to install requests if not already)
    location_info = get_location_info(request, ip_address)
    
    # Get referrer
    referrer = request.META.get('HTTP_REFERER', '')[:500]
    
    # Create scan record with FULL analytics
    try:
        scan_record = QRScan.objects.create(
            qr_code=qr_code,
            ip_address=ip_address,
            device_type=user_agent_info.get('device_type', 'desktop'),
            browser=user_agent_info.get('browser', 'unknown'),
            user_agent=user_agent_info.get('user_agent', ''),
            country=location_info.get('country', 'Unknown'),
            region=location_info.get('region', 'Unknown'),
            city=location_info.get('city', 'Unknown'),
            latitude=location_info.get('latitude', '0'),
            longitude=location_info.get('longitude', '0'),
            referrer=referrer
        )
        logger.info(f"Scan recorded: {scan_record.id} for QR {code}")
    except Exception as e:
        logger.error(f"Failed to create scan record: {e}")
        # Still create minimal record
        try:
            scan_record = QRScan.objects.create(
                qr_code=qr_code,
                ip_address=ip_address,
                device_type='desktop',
                browser='unknown',
                country='Unknown',
                city='Unknown'
            )
        except:
            pass  # Skip if still failing
    
    # Get the redirect URL
    redirect_url = qr_code.redirect_url or qr_code.final_url
    
    if not redirect_url:
        return HttpResponse("QR Code has no redirect URL", status=404)
    
    # Check if it's a special protocol
    special_protocols = ['geo:', 'tel:', 'mailto:', 'sms:', 'whatsapp:', 'upi:', 'wifi:', 'itms-apps:', 'spotify:', 'instagram:']
    
    if any(redirect_url.startswith(protocol) for protocol in special_protocols):
        # For special protocols, create a landing page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Redirecting...</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script>
                window.location.href = "{redirect_url}";
            </script>
        </head>
        <body>
            <p>Redirecting... If not redirected, <a href="{redirect_url}">click here</a>.</p>
        </body>
        </html>
        """
        return HttpResponse(html_content, content_type='text/html')
    
    # For regular HTTP/HTTPS URLs, redirect immediately
    return HttpResponseRedirect(redirect_url)

from datetime import timedelta  # Make sure this is at the top
import json  # Make sure this is imported
from django.db.models import Count
from django.db.models.functions import TruncDate

def analytics_dashboard(request, key):
    """Analytics dashboard for QR code with complete data"""
    qr_code = get_object_or_404(QRCode, analytics_key=key)
    #qr_code = get_object_or_404(QRCode, analytics_code=analytics_code)
    
    # Get analytics data
    scans = qr_code.scans.all()
    
    # Date range (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_scans = scans.filter(scanned_at__gte=thirty_days_ago)
    
    # ========== SCANS BY DATE (Chart) ==========
    scans_by_date_list = []
    try:
        scans_by_date_data = recent_scans.annotate(
            date=TruncDate('scanned_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        for item in scans_by_date_data:
            if item['date']:
                scans_by_date_list.append({
                    'date': item['date'].strftime('%Y-%m-%d'),
                    'count': item['count']
                })
    except Exception as e:
        logger.warning(f"Error getting scans by date: {e}")
    
    # If no data, create sample for chart
    if not scans_by_date_list:
        today = timezone.now().date()
        for i in range(7, 0, -1):
            date = today - timedelta(days=i)
            scans_by_date_list.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': 0
            })
    
    # ========== DEVICE BREAKDOWN (Chart) ==========
    device_breakdown_list = []
    try:
        device_data = scans.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for device in device_data:
            if device['device_type']:
                device_breakdown_list.append({
                    'device_type': device['device_type'],
                    'count': device['count']
                })
    except Exception as e:
        logger.warning(f"Device breakdown error: {e}")
        device_breakdown_list = [
            {'device_type': 'mobile', 'count': 0},
            {'device_type': 'desktop', 'count': 0},
            {'device_type': 'tablet', 'count': 0}
        ]
    
    # ========== BROWSER BREAKDOWN (Chart) ==========
    browser_breakdown_list = []
    try:
        browser_data = scans.values('browser').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for browser in browser_data:
            if browser['browser'] and browser['browser'].lower() != 'unknown':
                browser_breakdown_list.append({
                    'browser': browser['browser'],
                    'count': browser['count']
                })
    except Exception as e:
        logger.warning(f"Browser breakdown error: {e}")
        browser_breakdown_list = [
            {'browser': 'chrome', 'count': 0},
            {'browser': 'safari', 'count': 0},
            {'browser': 'firefox', 'count': 0}
        ]
    
    # ========== TOP CITIES (Table) - FIXED ==========
    top_cities_list = []
    try:
        # First, check if we have any scan data
        if scans.exists():
            # Try to get city/country data
            location_data = scans.filter(
                city__isnull=False
            ).exclude(
                city__in=['', 'Unknown', 'unknown', None]
            ).values(
                'city', 'country'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            for loc in location_data:
                top_cities_list.append({
                    'city': loc['city'] or 'Unknown',
                    'country': loc['country'] or 'Unknown',
                    'count': loc['count']
                })
            
            # If still empty, show scans with unknown locations
            if not top_cities_list and scans.exists():
                top_cities_list.append({
                    'city': 'Unknown Location',
                    'country': 'Unknown',
                    'count': scans.count()
                })
    except Exception as e:
        logger.warning(f"Location data error: {e}")
        top_cities_list = [{'city': 'Unknown', 'country': 'Unknown', 'count': 0}]
    
    # ========== LAST SCANNED TIME ==========
    last_scanned_time = None
    if scans.exists():
        last_scan = scans.order_by('-scanned_at').first()
        last_scanned_time = last_scan.scanned_at
    
    # ========== CONTEXT DATA ==========
    context = {
        'qr_code': qr_code,
        'total_scans': scans.count(),
        'recent_scans_count': recent_scans.count(),
        'scans_by_date': json.dumps(scans_by_date_list),
        'device_breakdown': json.dumps(device_breakdown_list),
        'browser_breakdown': json.dumps(browser_breakdown_list),
        'top_cities': top_cities_list,  # This should be a Python list, NOT JSON
        'last_scanned': last_scanned_time,
    }
    
    # Debug output - check what's in context
    logger.info(f"Analytics context - Total scans: {scans.count()}")
    logger.info(f"Top cities count: {len(top_cities_list)}")
    for city in top_cities_list[:3]:
        logger.info(f"City: {city}")
    
    return render(request, 'qrtools/analytics.html', context)
def profile_card_view(request, code):
    """Display beautiful profile card landing page"""
    
    qr_code = get_object_or_404(QRCode, analytics_code=code, qr_type='profile')
    profile_card = get_object_or_404(ProfileCard, qr_code=qr_code)
    
    # Track view
    profile_card.increment_view()
    
    # Also track as scan
    qr_code.increment_scan()
    
    context = {
        'profile': profile_card,
        'qr_code': qr_code,
    }
    
    return render(request, 'qrtools/profile_card.html', context)


@require_http_methods(["POST"])
def bulk_generate_api(request):
    """Bulk QR code generation"""
    try:
        data = json.loads(request.body)
        
        batch_data = data.get('batch_data', [])
        design_template = data.get('design_template', {})
        batch_title = data.get('batch_title', f'Batch {timezone.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not batch_data:
            return JsonResponse({'error': 'No batch data provided'}, status=400)
        
        # Create batch
        batch = BulkQRBatch.objects.create(
            title=batch_title,
            total_codes=len(batch_data),
            design_template=design_template,
            status='processing'
        )
        
        generated_codes = []
        
        for item in batch_data:
            try:
                qr_type = item.get('qr_type', 'url')
                content_data = item.get('content_data', {})
                
                # Merge design template with item-specific overrides
                item_design = {**design_template, **item.get('design_config', {})}
                
                # Add box_size and border parameters
                size = item_design.get('size', 300)
                item_design['box_size'] = max(5, size // 30)
                item_design['border'] = 4
                
                # Build QR data
                qr_data = build_qr_data(qr_type, content_data)
                
                if not qr_data:
                    continue
                
                # Create QR code
                qr_code = QRCode.objects.create(
                    qr_type=qr_type,
                    content_data=content_data,
                    final_url=qr_data,
                    is_dynamic=item_design.get('is_dynamic', True),
                    folder_name=batch.title,
                    primary_color=item_design.get('primary_color', '#000000'),
                    background_color=item_design.get('background_color', '#FFFFFF'),
                    gradient_enabled=item_design.get('gradient_enabled', False),
                    gradient_color=item_design.get('gradient_color', ''),
                    frame_style=item_design.get('frame_style', 'none'),
                    pattern_style=item_design.get('pattern_style', 'square'),
                    has_logo=item_design.get('has_logo', False),
                    logo_url=item_design.get('logo_url', ''),
                    title=item_design.get('title', ''),
                    description=item_design.get('description', '')
                )
                
                # Generate QR
                if qr_code.is_dynamic:
                    actual_data = request.build_absolute_uri(qr_code.get_redirect_url())
                    qr_code.redirect_url = qr_data
                else:
                    actual_data = qr_data
                
                img = create_styled_qr(actual_data, item_design)
                
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
                qr_code.qr_image = f'data:image/png;base64,{img_str}'
                qr_code.save()
                
                generated_codes.append({
                    'analytics_code': qr_code.analytics_code,
                    'title': qr_code.title,
                    'qr_image': qr_code.qr_image,
                })
                
                batch.generated_codes += 1
                batch.save()
                
            except Exception as e:
                logger.error(f"Error generating QR in batch: {e}")
                continue
        
        batch.status = 'completed'
        batch.completed_at = timezone.now()
        batch.save()
        
        return JsonResponse({
            'success': True,
            'batch_id': str(batch.batch_id),
            'total_generated': batch.generated_codes,
            'qr_codes': generated_codes,
        })
        
    except Exception as e:
        logger.error(f"Bulk generation error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_templates_api(request):
    """Get available QR templates"""
    
    industry = request.GET.get('industry')
    
    templates = QRTemplate.objects.filter(is_active=True)
    if industry:
        templates = templates.filter(industry=industry)
    
    templates_data = [{
        'id': t.id,
        'name': t.name,
        'slug': t.slug,
        'description': t.description,
        'industry': t.industry,
        'preview_image': t.preview_image,
        'design_config': t.design_config,
        'is_premium': t.is_premium,
    } for t in templates]
    
    return JsonResponse({
        'success': True,
        'templates': templates_data,
    })


@require_http_methods(["POST"])
def update_dynamic_qr_api(request, code):
    """Update redirect URL for dynamic QR code"""
    try:
        qr_code = get_object_or_404(QRCode, analytics_code=code, is_dynamic=True)
        
        data = json.loads(request.body)
        new_url = data.get('redirect_url')
        
        if not new_url:
            return JsonResponse({'error': 'No redirect URL provided'}, status=400)
        
        # Update the URL
        qr_code.redirect_url = new_url
        qr_code.final_url = new_url  # Also update final_url for consistency
        qr_code.updated_at = timezone.now()
        qr_code.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Dynamic QR code updated successfully',
            'analytics_code': qr_code.analytics_code,
            'new_url': new_url,
            'updated_at': qr_code.updated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Update dynamic QR error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def bulk_download_api(request):
    """
    Download multiple QR codes as a ZIP file
    
    Request body:
    {
        "qr_codes": ["CODE1", "CODE2", ...],  // List of analytics_codes
        "format": "png",  // png, svg, pdf (optional)
        "include_data": true  // Include CSV with QR data (optional)
    }
    """
    try:
        data = json.loads(request.body)
        qr_codes_list = data.get('qr_codes', [])
        file_format = data.get('format', 'png').lower()
        include_data = data.get('include_data', False)
        
        if not qr_codes_list:
            return JsonResponse({'error': 'No QR codes selected'}, status=400)
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            csv_data = []
            csv_data.append(['Title', 'Type', 'Analytics Code', 'Analytics Key', 'Redirect URL', 'Total Scans', 'Created Date'])
            
            for idx, code in enumerate(qr_codes_list, 1):
                try:
                    qr_code = QRCode.objects.get(analytics_code=code)
                    
                    # Extract base64 image data
                    if qr_code.qr_image:
                        # Remove data:image/png;base64, prefix if present
                        img_data = qr_code.qr_image
                        if 'base64,' in img_data:
                            img_data = img_data.split('base64,')[1]
                        
                        img_bytes = base64.b64decode(img_data)
                        
                        # Generate filename
                        filename = f"{qr_code.title or qr_code.qr_type}_{qr_code.analytics_code}.png"
                        # Sanitize filename
                        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.')).rstrip()
                        
                        # Add to ZIP
                        zip_file.writestr(filename, img_bytes)
                        
                        # Add to CSV data
                        if include_data:
                            csv_data.append([
                                qr_code.title or '',
                                qr_code.qr_type,
                                qr_code.analytics_code,
                                qr_code.analytics_key,
                                qr_code.redirect_url or qr_code.final_url or '',
                                qr_code.total_scans,
                                qr_code.created_at.strftime('%Y-%m-%d %H:%M:%S')
                            ])
                    
                except QRCode.DoesNotExist:
                    logger.warning(f"QR code {code} not found")
                    continue
                except Exception as e:
                    logger.error(f"Error processing QR code {code}: {e}")
                    continue
            
            # Add CSV file if requested
            if include_data and len(csv_data) > 1:
                csv_content = '\n'.join([','.join([f'"{cell}"' for cell in row]) for row in csv_data])
                zip_file.writestr('qr_codes_data.csv', csv_content)
        
        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="qr_codes_bulk_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        
        return response
        
    except Exception as e:
        logger.error(f"Bulk download error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def bulk_download_by_folder_api(request):
    """
    Download all QR codes in a specific folder as ZIP
    
    Request body:
    {
        "folder_name": "My Folder",
        "include_data": true
    }
    """
    try:
        data = json.loads(request.body)
        folder_name = data.get('folder_name', '')
        include_data = data.get('include_data', False)
        
        if not folder_name:
            return JsonResponse({'error': 'Folder name required'}, status=400)
        
        # Get all QR codes in folder
        qr_codes = QRCode.objects.filter(folder_name=folder_name)
        
        if not qr_codes.exists():
            return JsonResponse({'error': 'No QR codes found in this folder'}, status=404)
        
        # Create ZIP file
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            csv_data = []
            csv_data.append(['Title', 'Type', 'Analytics Code', 'Analytics Key', 'Redirect URL', 'Total Scans', 'Created Date'])
            
            for qr_code in qr_codes:
                try:
                    if qr_code.qr_image:
                        # Extract image
                        img_data = qr_code.qr_image
                        if 'base64,' in img_data:
                            img_data = img_data.split('base64,')[1]
                        
                        img_bytes = base64.b64decode(img_data)
                        
                        # Filename
                        filename = f"{qr_code.title or qr_code.qr_type}_{qr_code.analytics_code}.png"
                        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.')).rstrip()
                        
                        zip_file.writestr(filename, img_bytes)
                        
                        # CSV data
                        if include_data:
                            csv_data.append([
                                qr_code.title or '',
                                qr_code.qr_type,
                                qr_code.analytics_code,
                                qr_code.analytics_key,
                                qr_code.redirect_url or qr_code.final_url or '',
                                qr_code.total_scans,
                                qr_code.created_at.strftime('%Y-%m-%d %H:%M:%S')
                            ])
                
                except Exception as e:
                    logger.error(f"Error processing QR code {qr_code.analytics_code}: {e}")
                    continue
            
            # Add CSV
            if include_data and len(csv_data) > 1:
                csv_content = '\n'.join([','.join([f'"{cell}"' for cell in row]) for row in csv_data])
                zip_file.writestr(f'{folder_name}_data.csv', csv_content)
        
        # Response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{folder_name}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        
        return response
        
    except Exception as e:
        logger.error(f"Folder bulk download error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def bulk_download_batch_api(request, batch_id):
    """
    Download all QR codes from a bulk generation batch
    
    URL: /api/bulk-download/batch/<batch_id>/
    """
    try:
        batch = get_object_or_404(BulkQRBatch, batch_id=batch_id)
        
        # Get all QR codes in this batch
        qr_codes = QRCode.objects.filter(folder_name=batch.title)
        
        if not qr_codes.exists():
            return JsonResponse({'error': 'No QR codes found in this batch'}, status=404)
        
        # Create ZIP
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            csv_data = []
            csv_data.append(['Title', 'Type', 'Analytics Code', 'Analytics Key', 'Redirect URL', 'Total Scans', 'Created Date'])
            
            for qr_code in qr_codes:
                try:
                    if qr_code.qr_image:
                        img_data = qr_code.qr_image
                        if 'base64,' in img_data:
                            img_data = img_data.split('base64,')[1]
                        
                        img_bytes = base64.b64decode(img_data)
                        
                        filename = f"{qr_code.title or qr_code.qr_type}_{qr_code.analytics_code}.png"
                        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.')).rstrip()
                        
                        zip_file.writestr(filename, img_bytes)
                        
                        csv_data.append([
                            qr_code.title or '',
                            qr_code.qr_type,
                            qr_code.analytics_code,
                            qr_code.analytics_key,
                            qr_code.redirect_url or qr_code.final_url or '',
                            qr_code.total_scans,
                            qr_code.created_at.strftime('%Y-%m-%d %H:%M:%S')
                        ])
                
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
            
            # Add CSV
            if len(csv_data) > 1:
                csv_content = '\n'.join([','.join([f'"{cell}"' for cell in row]) for row in csv_data])
                zip_file.writestr(f'{batch.title}_data.csv', csv_content)
        
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{batch.title}_{timezone.now().strftime("%Y%m%d")}.zip"'
        
        return response
        
    except Exception as e:
        logger.error(f"Batch download error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
@require_http_methods(["POST"])
@rate_limit(max_requests=5, window=60)  # Stricter rate limit for uploads
def upload_file_to_cloudinary(request):
    """
    API endpoint to upload files to Cloudinary and generate QR code from the file URL.
    
    Enhanced with:
    - Better error handling
    - File validation
    - Cloudinary timeout handling
    - CSRF protection
    """
    try:
        # Check if file is in request
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file size (10MB limit)
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        if uploaded_file.size > max_size:
            return JsonResponse({
                'error': f'File too large. Maximum size is {max_size / (1024 * 1024):.0f}MB'
            }, status=400)
        
        # Validate file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/mpeg', 'video/quicktime',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({
                'error': 'Unsupported file type. Please upload images, videos, or documents.'
            }, status=400)
        
        # Validate filename (security check)
        if not uploaded_file.name or len(uploaded_file.name) > 255:
            return JsonResponse({'error': 'Invalid filename'}, status=400)
        
        logger.info(f"Uploading file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Upload file to Cloudinary with error handling
        try:
            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                folder='21k_qr_files',
                resource_type='auto',
                timeout=60,
                chunk_size=6000000  # 6MB chunks for large files
            )
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            return JsonResponse({
                'error': 'File upload failed. Please try again or use a smaller file.'
            }, status=500)
        
        # Get the public URL from Cloudinary
        file_url = upload_result.get('secure_url')
        
        if not file_url:
            return JsonResponse({
                'error': 'Failed to get file URL from Cloudinary'
            }, status=500)
        
        # Get additional file info
        file_format = upload_result.get('format', 'unknown')
        file_type = upload_result.get('resource_type', 'unknown')
        cloudinary_size = upload_result.get('bytes', uploaded_file.size)
        
        # Generate QR code from the file URL
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            
            qr.add_data(file_url)
            qr.make(fit=True)
            
            # Create QR code image with professional colors
            img = qr.make_image(fill_color="#1e3a8a", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
        
        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return JsonResponse({
                'error': 'Failed to generate QR code from file URL'
            }, status=500)
        
        logger.info(f"File uploaded successfully: {uploaded_file.name}")
        
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'qr_image': f'data:image/png;base64,{img_str}',
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_format': file_format,
            'file_type': file_type,
            'cloudinary_size': cloudinary_size
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Upload failed. Please try again.'
        }, status=500)
