"""
Brewvino Booking Placecards Generator
A Streamlit application for generating formatted placecards from booking data CSV files.
"""

import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import json
import math
from datetime import datetime, timedelta

def load_design_specs(specs_file="design_specs.json"):
    """Load design specifications from JSON file"""
    try:
        with open(specs_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"Design specs file '{specs_file}' not found. Using default settings.")
        return get_default_specs()

def get_default_specs():
    """Return default design specifications"""
    return {
        "font_family": "Helvetica",
        "title_font_size": 14,
        "content_font_size": 12,
        "card_width": 3.5,
        "card_height": 2.5,
        "margin": 0.5,
        "background_color": "white",
        "text_color": "black",
        "border": True,
        "border_color": "gray"
    }

def generate_preview_card(design_specs):
    """Generate a preview image of a single placecard"""
    try:
        from reportlab.graphics import renderPM
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.lib.units import inch
        from reportlab.graphics.charts.textlabels import Label
        
        # Create a drawing for preview
        preview_width = 4 * inch
        preview_height = 3 * inch
        
        d = Drawing(preview_width, preview_height)
        
        # Background rectangle
        bg_color = colors.toColor(design_specs["background_color"])
        background = Rect(0, 0, preview_width, preview_height, 
                         fillColor=bg_color, strokeColor=None)
        d.add(background)
        
        # Border if enabled
        if design_specs["border"]:
            border_color = colors.toColor(design_specs.get("border_color", "gray"))
            border = Rect(0, 0, preview_width, preview_height, 
                         fillColor=None, strokeColor=border_color, strokeWidth=1)
            d.add(border)
        
        # Text elements
        text_color = colors.toColor(design_specs["text_color"])
        
        # RESERVED header
        reserved_label = Label()
        reserved_label.setOrigin(preview_width/2, preview_height * 0.85)
        reserved_label.setText("RESERVED")
        reserved_label.fontSize = design_specs["title_font_size"] + 2
        reserved_label.fontName = design_specs["font_family"]
        reserved_label.fillColor = text_color
        reserved_label.textAnchor = 'middle'
        d.add(reserved_label)
        
        # Line under RESERVED
        line_y = preview_height * 0.75
        line = Rect(preview_width * 0.1, line_y, preview_width * 0.8, 1,
                   fillColor=text_color, strokeColor=None)
        d.add(line)
        
        # Name
        name_label = Label()
        name_label.setOrigin(preview_width/2, preview_height * 0.6)
        name_label.setText("John Smith")
        name_label.fontSize = design_specs["title_font_size"]
        name_label.fontName = design_specs["font_family"]
        name_label.fillColor = text_color
        name_label.textAnchor = 'middle'
        d.add(name_label)
        
        # Time range
        time_label = Label()
        time_label.setOrigin(preview_width/2, preview_height * 0.45)
        time_label.setText("7:30 PM - 9:30 PM")
        time_label.fontSize = design_specs["content_font_size"]
        time_label.fontName = design_specs["font_family"]
        time_label.fillColor = text_color
        time_label.textAnchor = 'middle'
        d.add(time_label)
        
        # Table number (left)
        table_label = Label()
        table_label.setOrigin(preview_width * 0.15, preview_height * 0.2)
        table_label.setText("T5")
        table_label.fontSize = design_specs["content_font_size"]
        table_label.fontName = design_specs["font_family"]
        table_label.fillColor = text_color
        table_label.textAnchor = 'start'
        d.add(table_label)
        
        # Party size (right)
        party_label = Label()
        party_label.setOrigin(preview_width * 0.85, preview_height * 0.2)
        party_label.setText("4P")
        party_label.fontSize = design_specs["content_font_size"]
        party_label.fontName = design_specs["font_family"]
        party_label.fillColor = text_color
        party_label.textAnchor = 'end'
        d.add(party_label)
        
        # Render to PNG
        img_buffer = io.BytesIO()
        renderPM.drawToFile(d, img_buffer, fmt='PNG', dpi=150)
        img_buffer.seek(0)
        
        return img_buffer
        
    except Exception as e:
        st.error(f"Preview generation failed: {str(e)}")
        return None

def capitalize_customer_name(name):
    """Properly capitalize customer names"""
    if pd.isna(name) or name == "":
        return "Guest"
    
    # Convert to string and strip whitespace
    name = str(name).strip()
    
    # Handle special cases
    if name.lower() == "walk in":
        return "Walk In"
    
    # Split by spaces and capitalize each word
    words = name.split()
    capitalized_words = []
    
    for word in words:
        if word:  # Skip empty strings
            # Handle common prefixes and suffixes
            if word.lower() in ['mc', 'mac', 'o\'', 'de', 'van', 'von', 'la', 'le']:
                capitalized_words.append(word.capitalize())
            else:
                # Standard title case
                capitalized_words.append(word.capitalize())
    
    return ' '.join(capitalized_words)

def extract_table_numbers(table_string):
    """Extract and clean table numbers from table string, removing letters"""
    import re
    if pd.isna(table_string) or table_string == "":
        return "TBD"
    
    # Split by comma and clean each table
    tables = str(table_string).split(',')
    cleaned_tables = []
    
    for table in tables:
        # Extract only numbers from each table
        numbers = re.findall(r'\d+', table.strip())
        if numbers:
            cleaned_tables.append(numbers[0])  # Take first number found
    
    if cleaned_tables:
        return ','.join(cleaned_tables)
    else:
        return "TBD"

def calculate_end_time(booking_time):
    """Calculate end time by adding 2 hours to booking time"""
    try:
        # Try common time formats
        time_formats = [
            "%I:%M %p",      # 7:30 PM
            "%H:%M",         # 19:30
            "%I%p",          # 7PM
            "%I:%M%p",       # 7:30PM (no space)
        ]
        
        booking_datetime = None
        for fmt in time_formats:
            try:
                booking_datetime = datetime.strptime(booking_time.strip(), fmt)
                break
            except ValueError:
                continue
        
        if booking_datetime is None:
            # If parsing fails, return original time
            return f"{booking_time} - {booking_time}"
        
        # Add 2 hours
        end_datetime = booking_datetime + timedelta(hours=2)
        
        # Format both times consistently
        start_formatted = booking_datetime.strftime("%I:%M %p").lstrip('0')
        end_formatted = end_datetime.strftime("%I:%M %p").lstrip('0')
        
        return f"{start_formatted} - {end_formatted}"
        
    except Exception:
        # If any error occurs, return original time
        return f"{booking_time} - {booking_time}"

def validate_csv_structure(df):
    """Validate that the CSV has required columns"""
    required_columns = ["Service or Event", "Time", "Number of People", "Customer", "Table(s)"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        st.info("Required columns: Service or Event, Time, Number of People, Customer, Table(s)")
        return False
    return True

def generate_placecards(df, design_specs):
    """Generate PDF placecards from booking data in landscape 2x2 grid layout"""
    buffer = io.BytesIO()
    
    # Use landscape orientation
    page_size = landscape(letter)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=design_specs["margin"] * inch,
        leftMargin=design_specs["margin"] * inch,
        topMargin=design_specs["margin"] * inch,
        bottomMargin=design_specs["margin"] * inch
    )
    
    # Calculate available space for cards
    page_width = page_size[0] - (2 * design_specs["margin"] * inch)
    page_height = page_size[1] - (2 * design_specs["margin"] * inch)
    
    # Adjust card size to fit 2x2 grid with no spacing (borders touching)
    # Reduce height slightly to ensure 2 rows fit properly
    card_width = page_width / 2
    card_height = (page_height / 2) * 0.95  # Reduce height by 5% to ensure proper fit
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=design_specs["title_font_size"],
        textColor=colors.toColor(design_specs["text_color"]),
        alignment=TA_CENTER,
        fontName=design_specs["font_family"]
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['Normal'],
        fontSize=design_specs["content_font_size"],
        textColor=colors.toColor(design_specs["text_color"]),
        alignment=TA_CENTER,
        fontName=design_specs["font_family"]
    )
    
    story = []
    
    # Process bookings in groups of 4 (2x2 grid per page)
    for page_start in range(0, len(df), 4):
        page_bookings = df.iloc[page_start:page_start + 4]
        
        # Create 2x2 grid of cards
        page_data = []
        
        # First row (top left and top right cards)
        row1_cards = []
        for i in range(min(2, len(page_bookings))):
            row = page_bookings.iloc[i]
            card = create_single_card(row, title_style, content_style, design_specs, card_width, card_height)
            row1_cards.append(card)
        
        # Fill empty spots in first row if needed
        while len(row1_cards) < 2:
            row1_cards.append("")
        
        page_data.append(row1_cards)
        
        # Second row (bottom left and bottom right cards)
        row2_cards = []
        if len(page_bookings) > 2:
            for i in range(2, min(4, len(page_bookings))):
                row = page_bookings.iloc[i]
                card = create_single_card(row, title_style, content_style, design_specs, card_width, card_height)
                row2_cards.append(card)
        
        # Fill empty spots in second row if needed
        while len(row2_cards) < 2:
            row2_cards.append("")
        
        page_data.append(row2_cards)
        
        # Create the page table
        page_table = Table(
            page_data,
            colWidths=[card_width, card_width],
            rowHeights=[card_height, card_height]
        )
        
        # Apply table style with no padding (borders touching)
        page_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(page_table)
        
        # Add page break if there are more bookings
        if page_start + 4 < len(df):
            story.append(PageBreak())
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_single_card(row, title_style, content_style, design_specs, card_width, card_height):
    """Create a single placecard as a table"""
    # Create header style for "Reserved" title
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=title_style,
        fontSize=design_specs["title_font_size"] + 2,
        textColor=colors.toColor(design_specs["text_color"]),
        alignment=TA_CENTER,
        fontName=design_specs["font_family"],
        spaceBefore=6,
        spaceAfter=6
    )
    
    # Create styles for bottom row (left and right aligned)
    left_style = ParagraphStyle(
        'LeftStyle',
        parent=content_style,
        fontSize=design_specs["content_font_size"],
        textColor=colors.toColor(design_specs["text_color"]),
        alignment=0,  # Left alignment
        fontName=design_specs["font_family"]
    )
    
    right_style = ParagraphStyle(
        'RightStyle',
        parent=content_style,
        fontSize=design_specs["content_font_size"],
        textColor=colors.toColor(design_specs["text_color"]),
        alignment=2,  # Right alignment
        fontName=design_specs["font_family"]
    )
    
    # Create card content
    reserved_title = Paragraph("<b>RESERVED</b>", header_style)
    capitalized_name = capitalize_customer_name(row['Customer'])
    name = Paragraph(f"<b>{capitalized_name}</b>", title_style)
    time_range = calculate_end_time(row['Time'])
    time_info = Paragraph(f"{time_range}", content_style)
    empty_space = Paragraph("", content_style)
    
    # Extract and clean table numbers
    table_numbers = extract_table_numbers(row['Table(s)'])
    
    # Create bottom row with table and party info
    table_party_data = [
        [Paragraph(f"T{table_numbers}", left_style), 
         Paragraph(f"{row['Number of People']}P", right_style)]
    ]
    
    table_party_table = Table(
        table_party_data,
        colWidths=[card_width * 0.5, card_width * 0.5],  # Use full width
        rowHeights=[card_height * 0.2]
    )
    
    table_party_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),   # Left align table number
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Right align party size
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Create main table for card layout
    card_data = [
        [reserved_title],    # Header row
        [name],              # Name row
        [time_info],         # Time row
        [empty_space],       # Empty space row
        [table_party_table]  # Table/Party row
    ]
    
    card_table = Table(
        card_data,
        colWidths=[card_width],  # Use full card width
        rowHeights=[
            card_height * 0.25,  # Reserved header
            card_height * 0.25,  # Name
            card_height * 0.2,   # Time
            card_height * 0.1,   # Empty space
            card_height * 0.2    # Table/Party info
        ]
    )
    
    # Apply table style
    table_style = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.toColor(design_specs["background_color"])),
        # Add a line under the "Reserved" title
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.toColor(design_specs.get("border_color", "gray"))),
    ]
    
    if design_specs["border"]:
        table_style.append(('BOX', (0, 0), (-1, -1), 1, colors.toColor(design_specs["border_color"])))
    
    card_table.setStyle(TableStyle(table_style))
    
    return card_table

def main():
    st.title("🍷 Brewvino Booking Placecards Generator")
    st.markdown("Generate professional placecards for restaurant bookings from CSV data")
    
    # Load design specifications
    design_specs = load_design_specs()
    
    # File upload
    st.header("📄 Upload Booking Data")
    uploaded_file = st.file_uploader(
        "Choose a CSV file with booking data",
        type="csv",
        help="CSV should contain columns: Service or Event, Time, Number of People, Customer, Table(s)"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file, index_col=False)
            df2 = df.copy()[["Service or Event", "Time", "Number of People", "Customer", "Table(s)"]]
            
            # Show data preview
            st.subheader("Data Preview")
            st.dataframe(df2.head())
            
            # Validate structure
            if validate_csv_structure(df2):
                st.success(f"✅ Found {len(df2)} bookings in the uploaded file")
                
                # Service/Event filtering
                st.header("📅 Filter by Service Period")
                
                filter_option = st.radio(
                    "Choose which service to generate placecards for:",
                    ["All bookings", "Lunch only", "Dinner only"],
                    index=0,
                    help="Select whether to include all bookings or filter by service type"
                )
                
                # Apply filtering based on selection
                if filter_option == "Lunch only":
                    filtered_df = df2[df2['Service or Event'].str.lower().str.contains('lunch', na=False)]
                    st.info(f"📋 Filtered to {len(filtered_df)} **Lunch** bookings")
                elif filter_option == "Dinner only":
                    filtered_df = df2[df2['Service or Event'].str.lower().str.contains('dinner', na=False)]
                    st.info(f"📋 Filtered to {len(filtered_df)} **Dinner** bookings")
                else:
                    filtered_df = df2
                    st.info(f"📋 Including all {len(filtered_df)} bookings")
                
                # Show filtered data preview
                if len(filtered_df) > 0:
                    st.subheader("Filtered Data Preview")
                    st.dataframe(filtered_df.head())
                else:
                    st.warning("⚠️ No bookings found for the selected service period.")
                    st.stop()
                
                # Design customization
                st.header("🎨 Design Settings")
                st.info("📋 **Layout:** Landscape orientation with 4 cards per page (2x2 grid)")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    st.subheader("Font Settings")
                    design_specs["font_family"] = st.selectbox(
                        "Font Family",
                        ["Helvetica", "Times-Roman", "Courier"],
                        index=0 if design_specs["font_family"] == "Helvetica" else 1
                    )
                    design_specs["title_font_size"] = st.slider("Title Font Size", 10, 30, design_specs["title_font_size"])
                    design_specs["content_font_size"] = st.slider("Content Font Size", 8, 24, design_specs["content_font_size"])
                
                with col2:
                    st.subheader("Card Styling")
                    design_specs["border"] = st.checkbox("Show Border", design_specs["border"])
                    if design_specs["border"]:
                        design_specs["border_color"] = st.selectbox(
                            "Border Color",
                            ["gray", "black", "blue", "red", "green"],
                            index=0
                        )
                    design_specs["background_color"] = st.selectbox(
                        "Background Color",
                        ["white", "lightgray", "lightblue", "lightyellow"],
                        index=0
                    )
                
                with col3:
                    st.subheader("Preview")
                    st.write("Sample placecard with current settings:")
                    
                    # Generate and display preview
                    preview_buffer = generate_preview_card(design_specs)
                    if preview_buffer:
                        st.image(preview_buffer, caption="Placecard Preview", use_container_width=True)
                    else:
                        # Fallback text preview if image generation fails
                        st.code("""
┌─────────────────────────┐
│      **RESERVED**       │
│_________________________│
│     **John Smith**      │
│    7:30 PM - 9:30 PM    │
│                         │
│T5                     4P│
└─────────────────────────┘
                        """, language=None)
                
                # Generate placecards
                if st.button("🎫 Generate Placecards", type="primary"):
                    with st.spinner("Generating placecards..."):
                        try:
                            pdf_buffer = generate_placecards(filtered_df, design_specs)
                            
                            st.success("✅ Placecards generated successfully!")
                            
                            # Create filename based on service selection
                            if filter_option == "Lunch only":
                                filename = "brewvino_placecards_lunch.pdf"
                            elif filter_option == "Dinner only":
                                filename = "brewvino_placecards_dinner.pdf"
                            else:
                                filename = "brewvino_placecards_all_services.pdf"
                            
                            # Download button
                            st.download_button(
                                label="📥 Download Placecards PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=filename,
                                mime="application/pdf"
                            )
                            
                        except Exception as e:
                            st.error(f"Error generating placecards: {str(e)}")
        
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")
    
    # Instructions
    st.markdown("---")
    st.header("📋 Instructions")
    st.markdown("""
    1. **Prepare your CSV file** with the following columns:
       - `name`: Guest name
       - `table_number`: Table assignment
       - `booking_time`: Reservation time
       - `party_size`: Number of people in the party
    
    2. **Upload the CSV file** using the file uploader above
    
    3. **Customize the design** using the settings panel
    
    4. **Generate and download** your placecards as a PDF
    
    **Layout:** The PDF will be in landscape orientation with 4 placecards per page arranged in a 2×2 grid layout.
    Each placecard follows this format:
    ```
    ┌─────────────────────────┐
    │      **RESERVED**       │
    │_________________________│
    │     **John Smith**      │
    │    7:30 PM - 9:30 PM    │
    │                         │
    │T5                     4P│
    └─────────────────────────┘
    ```
    
    **Sample CSV format:**
    ```
    name,table_number,booking_time,party_size
    John Smith,5,7:30 PM,4
    Jane Doe,3,8:00 PM,2
    Mike Johnson,1,6:45 PM,6
    ```
    """)

if __name__ == "__main__":
    main()
