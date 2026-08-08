# Email Templates Module
# Converted from Google Apps Script to Python

COMPANY_INFO = {
    'EMAIL': 'booking@ftstravels.com',
    'PHONE': '+2 01030774440',
    'ADDRESS': '12h/4 Shawky Abdelmenim St., Maadi, Cairo',
    'NAME': 'FTS Travels',
    'LOGO': 'https://ftstravels.com/cropped-logo-2.png'
}

AI_DISCLAIMER = """
<div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; font-size: 11px; color: #6c757d; text-align: center; border: 1px solid #e9ecef;">
    Note: Farah (our Smart Assistant) may make mistakes. Our team is here to help.
</div>
"""

EMAIL_COLORS = {
    'primary': '#FF5722',
    'secondary': '#2196F3',
    'background': '#ECEFF1',
    'textLight': '#FFE0B2',
    'warning': '#fff3cd',
    'info': '#E3F2FD',
    'grey': '#f5f5f5'
}

BEACH_TRIPS = ['orange bay day trip', 'dolphin watching & snorkeling']
BEACH_TRIP_NOTE = 'What to bring: sunglasses, hat, swimwear, towel, sunscreen, and cash'

def is_beach_trip(trip_name):
    if not trip_name:
        return False
    trip_name_lower = trip_name.lower()
    return any(trip in trip_name_lower for trip in BEACH_TRIPS)

def generate_pickup_email_html(data):
    """
    Generates the HTML content for Pickup Details Email.
    Matches logic from 'Template Pickup.txt'.
    """
    customer_name = data.get('customerName', 'Guest')
    booking_nr = data.get('bookingNr', '')
    date_trip = data.get('dateTrip', '')
    pickup_time = data.get('pickupTime', '')
    hotel_name = data.get('hotelName', '')
    non_billable_addons = data.get('nonBillableAddons', '')
    add_ons = data.get('addOns', '')
    add_ons_multi = data.get('addOnsMulti', '')
    stripe_invoice = data.get('stripeInvoice', '') or data.get('stripe_invoice', '')
    trip_name = data.get('tripName', '')
    has_attachments = data.get('has_attachments', False)

    # Payment Notice
    cash_note = ''
    if add_ons:
        cash_note = f"""
        <div style="background-color:{EMAIL_COLORS['warning']};padding:15px;border:1px solid #ffeeba;border-radius:6px;margin-bottom:15px;">
        <strong>💰 Payment Notice:</strong> Please note that you have to pay cash for the following services on the day of the trip:<br>
        <b>{add_ons}</b>
        </div>
        """

    # Beach Trip Note
    beach_note = ''
    if is_beach_trip(trip_name):
        beach_note = f"""
        <div style="background-color:{EMAIL_COLORS['info']};padding:15px;border:1px solid #BEE5EB;border-radius:6px;margin-bottom:15px;">
        <strong>🏖️ {BEACH_TRIP_NOTE}</strong>
        </div>
        """
        
    # Attachments Note
    attachments_html = ''
    if has_attachments:
        attachments_html = f"""
        <h4>📎 Attachments:</h4>
        <div style="background: {EMAIL_COLORS['grey']}; padding: 10px; border-radius: 4px;">
            Please find the documents attached to this email.
        </div>
        """

    add_ons_multi_html = ''
    if add_ons_multi:
        add_ons_multi_html = f"""
        <h4>Add-Ons:</h4>
        <p>{add_ons_multi}</p>
        """

    payment_html = ''
    if stripe_invoice:
        payment_html = f"""
        <h3 style="color:green;"> Complete Your Payment</h3>
        <div style="text-align:center; margin:20px 0;">
            <a href="{stripe_invoice}" style="background-color:#4CAF50; color:white; padding:15px 30px; text-decoration:none; border-radius:8px; font-size:18px;">Pay Now</a>
        </div>
        <p style="color:#777; font-size:14px;">Please complete your payment to confirm your booking.</p>
        """

    html_content = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: {EMAIL_COLORS['background']}; padding: 30px;">
    <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
        
        <div style="background-color: {EMAIL_COLORS['primary']}; padding: 20px; text-align: center;">
            <img src="{COMPANY_INFO['LOGO']}" alt="{COMPANY_INFO['NAME']} Logo" style="max-height: 80px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0;">{COMPANY_INFO['NAME']}</h1>
            <p style="color: {EMAIL_COLORS['textLight']};">Booking Confirmation & Pickup Details</p>
        </div>

        <div style="padding: 25px;">
            <p>Dear <b>{customer_name}</b>,</p>
            
            <h3>🚐 Pickup Details:</h3>
            <p><b>Booking Number:</b> {booking_nr}</p>
            <p><b>Date:</b> {date_trip}</p>
            <p><b>Time:</b> {pickup_time}</p>
            <p><b>Location:</b> {hotel_name}</p>
            
            {f'<h4>📌 Note:</h4><p>{non_billable_addons}</p>' if non_billable_addons else ''}
            
            {add_ons_multi_html}

            {cash_note}
            {beach_note}
            {attachments_html}

            {payment_html}
            
            <h4>⏰ Be Ready on Time!</h4>
            <p>Kindly be ready 5 minutes before pickup. Driver waits up to 5 minutes.</p>
            
            <h4>✅ Check Your Belongings!</h4>
            <p>Please check all your items before leaving.</p>
            
            <h4>⚠️ Quick Confirmation Needed!</h4>
            <p>Reply to confirm your pickup details for priority support!</p>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="mailto:{COMPANY_INFO['EMAIL']}" style="background-color: {EMAIL_COLORS['secondary']}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px;">Contact Us</a>
            </div>
            
            <p style="font-size:12px; color:#888; text-align:center; margin-top: 20px;">
                {COMPANY_INFO['ADDRESS']} | {COMPANY_INFO['PHONE']} | {COMPANY_INFO['EMAIL']}
            </p>
            
            {AI_DISCLAIMER}
        </div>
    </div>
    </body></html>
    """
    return html_content

def generate_ticket_email(customer_name, full_trip_name, booking_nr, agency, pickup_time=None, hotel_name=None, has_attachments=False, trip_name=""):
    """
    Generates HTML email template for tickets.
    Matches logic from 'QR Send.txt'.
    """
    
    # Pickup Info Block
    pickup_html = ""
    if pickup_time and hotel_name:
        pickup_html = f"""
        <div style="background-color: {EMAIL_COLORS['info']}; padding: 15px; margin: 20px 0; border-radius: 6px;">
        <p><b>Pickup Information:</b><br>
        Your pickup time is at <b>{pickup_time}</b> from <b>{hotel_name}</b>.</p>
        </div>
        """

    # Beach Trip Note
    beach_note = ''
    if is_beach_trip(trip_name):
        beach_note = f"""
        <div style="background-color:{EMAIL_COLORS['info']};padding:15px;border:1px solid #BEE5EB;border-radius:6px;margin-bottom:15px;">
        <strong>🏖️ {BEACH_TRIP_NOTE}</strong>
        </div>
        """
        
    # Attachments Note
    attachments_html = ''
    if has_attachments:
        attachments_html = f"""
        <h4>📎 Attachments:</h4>
        <div style="background: {EMAIL_COLORS['grey']}; padding: 10px; border-radius: 4px;">
            Please see the attached tickets.
        </div>
        """
        
    html_content = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: {EMAIL_COLORS['background']}; padding: 30px;">
    <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 8px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
    <div style="background-color: {EMAIL_COLORS['primary']}; padding: 20px; text-align: center;">
    <img src="{COMPANY_INFO['LOGO']}" alt="{COMPANY_INFO['NAME']} Logo" style="max-height: 80px; margin-bottom: 10px;">
    <h1 style="color: white; margin: 0;">{COMPANY_INFO['NAME']}</h1>
    <p style="color: {EMAIL_COLORS['textLight']};">Your Entry Tickets</p></div>
    <div style="padding: 25px;">
    <p>Dear <b>{customer_name}</b>,</p>

    <p>Thank you for booking <b>{full_trip_name}</b> with {COMPANY_INFO['NAME']}!</p>

    {pickup_html}
    {beach_note}

    <div style="background-color: {EMAIL_COLORS['grey']}; padding: 15px; border-radius: 6px;">
    <p>⚠️ Please use only the attached tickets (not the Platform voucher).<br>If any issue happens, please call <b>{COMPANY_INFO['PHONE']}</b> before making any payment.</p>
    </div>

    {attachments_html}

    <div style="margin-top: 30px; text-align: center;">
    <a href="mailto:{COMPANY_INFO['EMAIL']}" style="background-color: {EMAIL_COLORS['secondary']}; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px;">Contact Us</a>
    </div>

    <p style="font-size:12px; color:#888; text-align:center;">{COMPANY_INFO['ADDRESS']} | {COMPANY_INFO['PHONE']} | {COMPANY_INFO['EMAIL']}</p>
    
    {AI_DISCLAIMER}

    </div></div></body></html>"""
    return html_content

def generate_airport_email_html(customer_name, booking_nr, full_trip_name):
    """
    Generates HTML for Airport Instructions.
    Matches logic from 'Template Pickup.txt'.
    """
    html_content = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: {EMAIL_COLORS['background']}; padding: 30px;">
    <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
        <div style="background-color: {EMAIL_COLORS['primary']}; padding: 20px; text-align: center;">
            <img src="{COMPANY_INFO['LOGO']}" alt="{COMPANY_INFO['NAME']} Logo" style="max-height: 80px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0;">{COMPANY_INFO['NAME']}</h1>
            <p style="color: {EMAIL_COLORS['textLight']};">Important Airport Instructions</p>
        </div>
        <div style="padding: 25px;">
            <p>Dear <b>{customer_name}</b>,</p>
            <p>Regarding your booking <b>{full_trip_name}</b> ({booking_nr}):</p>
            
            <div style="background-color: {EMAIL_COLORS['info']}; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {EMAIL_COLORS['secondary']};">
                <h3 style="margin-top: 0; color: {EMAIL_COLORS['primary']};">🛬 Important Airport Information:</h3>
                <p><strong>We kindly inform you that upon your arrival at the airport, you will need to exit the arrival hall entirely and proceed to the outside area. Our guide will be waiting for you outside the terminal, holding a sign bearing our company name, FTS, for easy identification.</strong></p>
                <p><strong>Should you require any assistance, please do not hesitate to contact us at any time.</strong></p>
            </div>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="tel:{COMPANY_INFO['PHONE']}" style="background-color: {EMAIL_COLORS['secondary']}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin-right: 10px;">Call Us</a>
                <a href="mailto:{COMPANY_INFO['EMAIL']}" style="background-color: {EMAIL_COLORS['primary']}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px;">Email Us</a>
            </div>
            
            <p style="margin-top: 30px; text-align: center; color: {EMAIL_COLORS['primary']}; font-weight: bold; font-size: 16px;">Best regards,<br>FTS Travels Team</p>
            <p style="font-size:12px; color:#888; text-align:center; margin-top: 20px;">{COMPANY_INFO['ADDRESS']}<br>{COMPANY_INFO['PHONE']} | {COMPANY_INFO['EMAIL']}</p>
        </div>
    </div>
    </body></html>
    """
    return html_content

def generate_standard_email_template(content, title="Response from FTS Travels", customer_name="Guest", signature=None, include_disclaimer=True):
    """
    Generates a standard email template for general responses.
    """
    signature_html = ""
    if signature:
        signature_html = f"""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px dashed #ddd; font-weight: bold; color: {EMAIL_COLORS['primary']};">
            {signature.replace('\\n', '<br>')}
        </div>
        """
        
    disclaimer_html = AI_DISCLAIMER if include_disclaimer else ""

    html_content = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: {EMAIL_COLORS['background']}; padding: 30px;">
    <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
        
        <div style="background-color: {EMAIL_COLORS['primary']}; padding: 20px; text-align: center;">
            <img src="{COMPANY_INFO['LOGO']}" alt="{COMPANY_INFO['NAME']} Logo" style="max-height: 80px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0;">{COMPANY_INFO['NAME']}</h1>
            <p style="color: {EMAIL_COLORS['textLight']};">{title}</p>
        </div>

        <div style="padding: 25px;">
            <p>Dear <b>{customer_name}</b>,</p>
            
            <div style="line-height: 1.6; color: #333;">
                {content}
            </div>
            
            {signature_html}
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="mailto:{COMPANY_INFO['EMAIL']}" style="background-color: {EMAIL_COLORS['secondary']}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px;">Contact Us</a>
            </div>
            
            <p style="font-size:12px; color:#888; text-align:center; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px;">
                {COMPANY_INFO['ADDRESS']} <br>
                {COMPANY_INFO['PHONE']} | {COMPANY_INFO['EMAIL']} <br>
                <a href="https://ftstravels.com" style="color: {EMAIL_COLORS['primary']}; text-decoration: none;">www.ftstravels.com</a>
            </p>
            
            {disclaimer_html}
        </div>
    </div>
    </body></html>
    """
    return html_content

def generate_missing_info_email(customer_name, trip_name, booking_nr, date_trip, missing_fields):
    """
    Generates HTML email for requesting specific missing information.
    """
    fields_list = "".join([f"<li>{field}</li>" for field in missing_fields])
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; background-color: {EMAIL_COLORS['background']}; padding: 30px; margin: 0;">
      <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 8px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background-color: {EMAIL_COLORS['primary']}; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
          <img src="{COMPANY_INFO['LOGO']}" alt="{COMPANY_INFO['NAME']} Logo" style="max-height: 80px; margin-bottom: 10px;">
          <h1 style="color: white; margin: 0;">{COMPANY_INFO['NAME']}</h1>
          <p style="color: {EMAIL_COLORS['textLight']}; margin: 5px 0 0;">Action Required</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 25px;">
          <p style="font-size: 18px;">Dear <b>{customer_name}</b>,</p>
          
          <p>We are preparing for your trip <b>{trip_name}</b> on <b>{date_trip}</b>.</p>
          <p>Booking Number: <b>{booking_nr}</b></p>
          
          <div style="background-color: {EMAIL_COLORS['warning']}; padding: 15px; border-radius: 6px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <p style="margin-top: 0; color: #d32f2f; font-weight: bold;">⚠️ To confirm your pickup time, we urgently need the following information:</p>
            <ul style="margin-bottom: 0;">
              {fields_list}
            </ul>
          </div>
          
          <p>Please reply to this email with these details as soon as possible.</p>
          
          <!-- Contact Button -->
          <div style="margin-top: 30px; text-align: center;">
            <a href="mailto:{COMPANY_INFO['EMAIL']}" 
               style="background-color: {EMAIL_COLORS['secondary']}; color: white; padding: 12px 30px; font-size: 16px; text-decoration: none; border-radius: 8px; display: inline-block;">
               Reply Now
            </a>
          </div>
          
          <!-- Footer -->
          <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="font-size: 12px; color: #999; margin-bottom: 5px;">{COMPANY_INFO['ADDRESS']}</p>
            <p style="font-size: 12px; color: #999; margin-top: 0;">📞 {COMPANY_INFO['PHONE']} | ✉️ {COMPANY_INFO['EMAIL']}</p>
            {AI_DISCLAIMER}
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return html_content
