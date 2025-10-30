import io
import cv2
import numpy as np
from PIL import Image
import streamlit as st
from streamlit_cropper import st_cropper

# ---------- Image Processing Utilities ----------
# (No changes in this section)

def to_gray(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

def enhance_contrast(gray, clip=2.0, tiles=8):
    """This is the 'Black & White' (formerly Enhanced) style"""
    clahe = cv2.createCLAHE(clipLimit=float(clip), tileGridSize=(tiles, tiles))
    return clahe.apply(gray)

def adjust_brightness_contrast(bgr, brightness=0, contrast=1.0):
    """Adjusts brightness and contrast"""
    return cv2.convertScaleAbs(bgr, alpha=float(contrast), beta=int(brightness))

def bgr_to_pil(img):
    """Convert BGR (OpenCV) to PIL Image"""
    if len(img.shape) == 2: # Grayscale
        return Image.fromarray(img).convert("RGB")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

def process_image(bgr, settings):
    """
    Applies all transformations from a settings dictionary to a BGR image.
    Order: Rotate -> Bright/Contrast -> Style
    """
    # 1. Rotate
    if settings["rotate"] == 90:
        processed_bgr = cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    elif settings["rotate"] == 180:
        processed_bgr = cv2.rotate(bgr, cv2.ROTATE_180)
    elif settings["rotate"] == 270:
        processed_bgr = cv2.rotate(bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        processed_bgr = bgr

    # 2. Brightness & Contrast
    processed_bgr = adjust_brightness_contrast(
        processed_bgr,
        settings["brightness"],
        settings["contrast"]
    )

    # 3. Style
    if settings["style"] == "Black & White":
        gray = to_gray(processed_bgr)
        processed_img = enhance_contrast(gray, clip=2.0) # Using hardcoded clip
    elif settings["style"] == "Original":
        if len(processed_bgr.shape) == 3:
            processed_img = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
        else:
            processed_img = processed_bgr
    
    # Convert final processed image (which might be BGR or Gray) to PIL
    if len(processed_img.shape) == 2:
        return Image.fromarray(processed_img).convert("RGB")
    else:
        return Image.fromarray(processed_img)


# ---------- Session State & Callbacks ----------

def initialize_state(uploads):
    """
    Reads uploaded files into session state as a list of dictionaries.
    Each dict holds the original image and its unique settings.
    """
    current_file_ids = [up.file_id for up in uploads] 

    if "file_ids" not in st.session_state or st.session_state.file_ids != current_file_ids:
        
        st.session_state.file_ids = current_file_ids
        st.session_state.images = []
        st.session_state.current_index = 0
        
        for up in uploads:
            file_bytes = np.asarray(bytearray(up.read()), dtype=np.uint8)
            bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            st.session_state.images.append({
                "file_id": up.file_id, # --- NEW: Store the unique file_id
                "original_bgr": bgr,
                "name": up.name,
                "settings": {
                    "style": "Original",
                    "brightness": 0,
                    "contrast": 1.0,
                    "rotate": 0,
                }
            })
    
    if st.session_state.current_index >= len(st.session_state.images):
        st.session_state.current_index = 0

# (No changes to next_image, prev_image, rotate_current_image, 
#  apply_to_all, or update_current_image_settings)

def next_image():
    if st.session_state.current_index < len(st.session_state.images) - 1:
        st.session_state.current_index += 1

def prev_image():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

def rotate_current_image():
    idx = st.session_state.current_index
    current_rotate = st.session_state.images[idx]["settings"]["rotate"]
    new_rotate = (current_rotate + 90) % 360
    st.session_state.images[idx]["settings"]["rotate"] = new_rotate

def apply_to_all():
    current_settings = {
        "style": st.session_state.current_style,
        "brightness": st.session_state.current_brightness,
        "contrast": st.session_state.current_contrast,
        "rotate": st.session_state.images[st.session_state.current_index]["settings"]["rotate"]
    }
    
    for i in range(len(st.session_state.images)):
        st.session_state.images[i]["settings"] = current_settings.copy()

def update_current_image_settings():
    idx = st.session_state.current_index
    st.session_state.images[idx]["settings"]["style"] = st.session_state.current_style
    st.session_state.images[idx]["settings"]["brightness"] = st.session_state.current_brightness
    st.session_state.images[idx]["settings"]["contrast"] = st.session_state.current_contrast


# ---------- Streamlit UI ----------
st.set_page_config(page_title="Document Editor", layout="wide")
st.title("📄 Document Editor & PDF Converter")

# Initialize session state
if "images" not in st.session_state:
    st.session_state.images = []
    st.session_state.current_index = 0
    st.session_state.file_ids = []

uploads = st.file_uploader(
    "Upload one or more images",
    type=["jpg","jpeg","png"],
    accept_multiple_files=True
)

if uploads:
    # 1. Load/initialize images and settings into state
    initialize_state(uploads)
    
    idx = st.session_state.current_index
    current_image_data = st.session_state.images[idx]
    current_settings = current_image_data["settings"]

    st.markdown("---")
    
    # 2. Main Editor UI (Controls + Image)
    col1, col2 = st.columns([0.35, 0.65])
    with col1:
        st.subheader(f"Editing: {current_image_data['name']}")
        st.caption(f"Image {idx + 1} of {len(st.session_state.images)}")

        nav_col1, nav_col2 = st.columns(2)
        nav_col1.button("⬅️ Previous", on_click=prev_image, disabled=(idx == 0), use_container_width=True)
        nav_col2.button("Next ➡️", on_click=next_image, disabled=(idx == len(uploads) - 1), use_container_width=True)
        
        st.markdown("---")
        
        st.radio(
            "Choose output style",
            ["Original", "Black & White"],
            key="current_style",
            index=["Original", "Black & White"].index(current_settings["style"]),
            on_change=update_current_image_settings
        )
        st.slider(
            "Brightness", -100, 100,
            value=current_settings["brightness"],
            key="current_brightness",
            on_change=update_current_image_settings
        )
        st.slider(
            "Contrast", 0.0, 3.0,
            value=current_settings["contrast"],
            step=0.1,
            key="current_contrast",
            on_change=update_current_image_settings
        )
        st.button("Rotate 90° ↻", on_click=rotate_current_image, use_container_width=True)
        st.markdown("---")
        st.button("Apply these settings to ALL images", on_click=apply_to_all, use_container_width=True)
        
    with col2:
        st.subheader("Live Preview")
        
        original_rgb_pil = Image.fromarray(cv2.cvtColor(current_image_data["original_bgr"], cv2.COLOR_BGR2RGB))
        
        cropped_pil_img = st_cropper(
            original_rgb_pil,
            realtime_update=True,
            box_color='blue',
            aspect_ratio=None,
            key=f"cropper_{idx}"
        )
        
        cropped_bgr_np = cv2.cvtColor(np.array(cropped_pil_img), cv2.COLOR_RGB2BGR)
        final_processed_pil = process_image(cropped_bgr_np, current_settings)
        st.image(final_processed_pil, caption="Final Processed Preview", use_container_width=True)

    
    # 3. Reorder & Download Section
    st.markdown("---")
    st.header("Reorder & Download PDFs")
    
    # --- NEW: Reordering UI ---
    st.subheader("Drag and Drop to Reorder Pages")
    st.caption("This order will be used for the 'Combined PDF' download.")
    
    # Create a simplified list for the data_editor
    display_list = []
    for i, img_data in enumerate(st.session_state.images):
        display_list.append({
            "Page": f"{i+1}",
            "File Name": img_data["name"],
            "Style": img_data["settings"]["style"],
            "Rotation": img_data["settings"]["rotate"],
            "file_id": img_data["file_id"] # Keep for mapping
        })
    
    # Use st.data_editor to allow reordering
    edited_display_list = st.data_editor(
        display_list,
        column_config={
            "file_id": None, # Hide the ID column
            "Page": st.column_config.TextColumn(disabled=True),
            "File Name": st.column_config.TextColumn(disabled=True),
            "Style": st.column_config.TextColumn(disabled=True),
            "Rotation": st.column_config.NumberColumn(disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key="page_order_editor"
    )
    
    # --- NEW: Check for order changes and update session_state ---
    old_file_id_order = [d["file_id"] for d in display_list]
    new_file_id_order = [d["file_id"] for d in edited_display_list]
    
    if old_file_id_order != new_file_id_order:
        # Reorder the "master" st.session_state.images list
        new_image_data_list = []
        # Create a lookup map for efficiency
        image_data_map = {img['file_id']: img for img in st.session_state.images}
        
        for file_id in new_file_id_order:
            new_image_data_list.append(image_data_map[file_id])
        
        st.session_state.images = new_image_data_list
        # Rerun to update the "Page" numbers in the editor
        st.rerun()

    # --- PDF Generation (No changes needed here) ---
    # This loop now naturally respects the new order of st.session_state.images
    pdf_pages = []
    with st.spinner("Generating PDF previews... (Note: Crop is not saved yet)"):
        for img_data in st.session_state.images:
            pil_page = process_image(img_data["original_bgr"], img_data["settings"])
            pdf_pages.append(pil_page)

    st.markdown("### Download per-image PDFs")
    st.caption("Note: Downloads are based on saved settings (rotation, style, etc.), but **not the live crop**.")
    
    cols = st.columns(3)
    # This list is now in the user-defined order, which is fine
    for i, pil_page in enumerate(pdf_pages):
        buf = io.BytesIO()
        pil_page.save(buf, format="PDF")
        
        # Get the original name from the reordered list
        file_name = st.session_state.images[i]["name"]
        
        cols[i % 3].download_button(
            f"⬇️ Download '{file_name}.pdf'",
            data=buf.getvalue(),
            file_name=f"{file_name}.pdf",
            mime="application/pdf",
            key=f"single_{i}"
        )

    # Combined PDF
    if len(pdf_pages) > 1:
        st.markdown("### Or download all as a single PDF")
        combo = io.BytesIO()
        first, rest = pdf_pages[0], pdf_pages[1:]
        first.save(combo, format="PDF", save_all=True, append_images=rest)
        
        st.download_button(
            "⬇️ Download Combined PDF",
            data=combo.getvalue(),
            file_name="documents_combined.pdf",
            mime="application/pdf",
            type="primary"
        )
else:
    st.info("Upload one or more images to begin.")