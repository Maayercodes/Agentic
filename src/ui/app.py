import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from sqlalchemy import func

from src.database.models import init_db, Daycare, Influencer, Region, Platform
from src.ai_assistant.assistant import AIAssistant
from src.scrapers.daycare_scraper import DaycareGoogleMapsScraper
from src.scrapers.influencer_scraper import InfluencerScraper

load_dotenv()

# Initialize session state
if 'assistant' not in st.session_state:
    session = init_db()
    st.session_state.assistant = AIAssistant(session)
    st.session_state.daycare_scraper = DaycareGoogleMapsScraper(api_key=os.getenv("SERPAPI_API_KEY"))
    st.session_state.influencer_scraper = InfluencerScraper(session)

def main():
    st.set_page_config(page_title="AI Marketing Outreach Platform", layout="wide")
    
    st.title("🤖 AI Marketing Outreach Platform")
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Data Collection", "AI Assistant", "Outreach Campaigns", "Analytics"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Data Collection":
        show_data_collection()
    elif page == "AI Assistant":
        show_ai_assistant()
    elif page == "Outreach Campaigns":
        show_outreach_campaigns()
    elif page == "Analytics":
        show_analytics()

def show_dashboard():
    st.header("📊 Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Daycares", len(st.session_state.assistant.session.query(Daycare).all()))
    
    with col2:
        st.metric("Total Influencers", len(st.session_state.assistant.session.query(Influencer).all()))
    
    with col3:
        total_emails = st.session_state.assistant.session.query(Daycare).filter(Daycare.last_contacted.isnot(None)).count() + \
                      st.session_state.assistant.session.query(Influencer).filter(Influencer.last_contacted.isnot(None)).count()
        st.metric("Emails Sent", total_emails)

def show_data_collection():
    st.header("🔍 Data Collection")
    
    tab1, tab2 = st.tabs(["Daycare Scraping", "Influencer Scraping"])
    
    with tab1:
        st.subheader("Daycare Data Collection")
        
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox("Select Country", ["USA", "FRANCE"])
        
        with col2:
            if country == "USA":
                city = st.text_input("Enter City")
                state = st.text_input("Enter State (e.g., NY)")
            else:
                city = st.text_input("Enter City")
                state = None
        
        if st.button("Start Daycare Scraping"):
            with st.spinner("Scraping daycare data..."):
                cities = [{'city': city, 'state': state, 'country': country}]
                st.session_state.daycare_scraper.scrape_all(cities)
                st.success("Scraping completed!")
    
    with tab2:
        st.subheader("Influencer Data Collection")
        
        keywords = st.text_area(
            "Enter keywords (one per line)",
            "parenting tips\nearly childhood education\nkids activities"
        ).split('\n')
        
        if st.button("Start Influencer Scraping"):
            with st.spinner("Scraping influencer data..."):
                st.session_state.influencer_scraper.scrape_all(keywords)
                st.success("Scraping completed!")

def show_ai_assistant():
    st.header("🧠 AI Assistant")
    
    user_input = st.text_input(
        "Enter your command",
        placeholder="e.g., 'Find all influencers in France with 10k+ followers'"
    )
    
    if user_input:
        with st.spinner("Processing your request..."):
            result = asyncio.run(st.session_state.assistant.process_command(user_input))
            
            if 'error' in result:
                st.error(result['error'])
            else:
                if 'influencers' in result:
                    st.dataframe(pd.DataFrame(result['influencers']))
                elif 'daycares' in result:
                    st.dataframe(pd.DataFrame(result['daycares']))
                elif 'success' in result:
                    st.success(f"Successfully sent {result['messages_sent']} messages!")

def show_outreach_campaigns():
    st.header("📤 Outreach Campaigns")
    
    # Step 1: Configure campaign
    st.subheader("1. Configure Campaign")
    col1, col2 = st.columns(2)
    
    with col1:
        target_type = st.selectbox("Select Target Type", ["daycare", "influencer"])
        count = st.number_input("Number of Recipients", min_value=1, max_value=100, value=10)
    
    with col2:
        if target_type == "daycare":
            region = st.selectbox("Select Region", ["USA", "FRANCE"])
        else:
            region = None
    
    # Step 2: Email Content
    st.subheader("2. Email Content")
    use_template = st.checkbox("Use default template", value=True)
    
    if use_template:
        st.info("Using default email template for selected target type and region.")
        custom_subject = None
        custom_body = None
    else:
        custom_subject = st.text_input("Email Subject Line")
        custom_body = st.text_area("Email Body", height=200)
        
        if not custom_subject or not custom_body:
            st.warning("Please provide both subject and body for your custom email.")
    
    # Step 3: Sender Configuration
    st.subheader("3. Sender Configuration")
    sender_email = st.text_input("Sender Email Address", value=os.getenv('GMAIL_USER', ''))
    sender_name = st.text_input("Sender Name", value=os.getenv('EMAIL_SENDER_NAME', 'AI Marketing Outreach'))
    
    if not sender_email:
        st.warning("Please provide a sender email address.")
    
    # Preview and Send
    if st.button("Preview Campaign"):
        # Get target recipients
        with st.spinner("Loading recipients..."):
            # Query for targets based on criteria
            session = st.session_state.assistant.session
            
            if target_type == 'daycare':
                query = session.query(Daycare).filter(Daycare.last_contacted == None)
                if region:
                    query = query.filter(Daycare.region == region)
                targets = query.order_by(func.random()).limit(count).all()
            else:  # influencer
                query = session.query(Influencer).filter(Influencer.last_contacted == None)
                targets = query.order_by(func.random()).limit(count).all()
            
            if not targets:
                st.error(f"No {target_type}s found matching your criteria.")
            else:
                # Display preview
                st.subheader("📧 Email Preview")
                
                # Show email content
                preview_col1, preview_col2 = st.columns(2)
                
                with preview_col1:
                    st.markdown("**From:**")
                    st.info(f"{sender_name} <{sender_email}>")
                    
                    st.markdown("**Subject:**")
                    if use_template:
                        # Get template subject (simplified for preview)
                        subject = f"AI Storytelling Platform for {target_type.capitalize()}s"
                    else:
                        subject = custom_subject
                    st.info(subject)
                
                with preview_col2:
                    st.markdown("**Email Body:**")
                    if use_template:
                        # Simplified template preview
                        st.info(f"Default {target_type.capitalize()} template will be used and personalized for each recipient.")
                    else:
                        st.info(custom_body)
                
                # Show recipients
                st.subheader(f"Recipients ({len(targets)})")
                recipients_df = pd.DataFrame([
                    {
                        "Name": getattr(t, 'name', 'Unknown'),
                        "Email": getattr(t, 'email', 'Unknown'),
                        "City": getattr(t, 'city', 'Unknown') if target_type == 'daycare' else '',
                        "Region/Platform": getattr(t, 'region', '') if target_type == 'daycare' else getattr(t, 'platform', '').value if hasattr(getattr(t, 'platform', ''), 'value') else ''
                    } for t in targets
                ])
                st.dataframe(recipients_df)
                
                # Confirmation
                st.subheader("Confirm Sending")
                st.warning("Please review the email content and recipients carefully before sending.")
                
                if st.button("Send Emails"):
                    with st.spinner("Sending emails..."):
                        # Prepare command with custom content if provided
                        command_parts = [f"Send outreach email to {count} random"]
                        if region:
                            command_parts.append(region)
                        command_parts.append(f"{target_type}s")
                        
                        if not use_template:
                            command_parts.append(f"with subject '{custom_subject}' and body '{custom_body}'")
                        
                        if sender_email != os.getenv('GMAIL_USER', ''):
                            command_parts.append(f"from {sender_email}")
                            
                        command = " ".join(command_parts)
                        
                        # Process command
                        result = asyncio.run(st.session_state.assistant.process_command(command))
                        
                        if 'error' in result:
                            st.error(result['error'])
                        else:
                            st.success(f"Campaign completed! Sent {result.get('messages_sent', 0)} emails.")
                            st.json(result.get('details', {}))
                else:
                    st.info("No emails have been sent yet. Click 'Send Emails' to proceed.")


def show_analytics():
    st.header("📈 Analytics")
    
    # Email statistics
    st.subheader("Email Campaign Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sent = st.session_state.assistant.session.query(Daycare).filter(Daycare.last_contacted.isnot(None)).count() + \
                     st.session_state.assistant.session.query(Influencer).filter(Influencer.last_contacted.isnot(None)).count()
        st.metric("Total Emails Sent", total_sent)
    
    with col2:
        total_opened = st.session_state.assistant.session.query(Daycare).filter(Daycare.email_opened == True).count() + \
                      st.session_state.assistant.session.query(Influencer).filter(Influencer.email_opened == True).count()
        st.metric("Emails Opened", total_opened)
    
    with col3:
        total_replied = st.session_state.assistant.session.query(Daycare).filter(Daycare.email_replied == True).count() + \
                       st.session_state.assistant.session.query(Influencer).filter(Influencer.email_replied == True).count()
        st.metric("Replies Received", total_replied)
    
    with col4:
        if total_sent > 0:
            response_rate = (total_replied / total_sent) * 100
            st.metric("Response Rate", f"{response_rate:.1f}%")
    
    # Export Data Section
    st.header("📥 Export Contact Data")
    
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        export_target_type = st.selectbox("Select Contact Type to Export", ["daycare", "influencer"], key="export_target")
        
    with export_col2:
        if export_target_type == "daycare":
            export_region = st.selectbox("Filter by Region", ["All Regions", "USA", "FRANCE"], key="export_region")
        else:
            export_region = st.selectbox("Filter by Country", ["All Countries", "USA", "France"], key="export_country")
    
    if st.button("Export to CSV"):
        with st.spinner("Preparing export..."):
            # Prepare command
            command = f"Export {export_target_type}s"
            if export_region and export_region not in ["All Regions", "All Countries"]:
                command += f" in {export_region}"
            command += " to CSV"
            
            # Process command
            result = asyncio.run(st.session_state.assistant.process_command(command))
            
            if 'error' in result:
                st.error(result['error'])
            else:
                # Create download link
                file_path = result.get('file_path')
                file_name = result.get('file_name')
                contact_count = result.get('contact_count', 0)
                
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        csv_data = f.read()
                    
                    st.success(f"Successfully exported {contact_count} {export_target_type}s to CSV!")
                    st.download_button(
                        label=f"Download {file_name}",
                        data=csv_data,
                        file_name=file_name,
                        mime="text/csv"
                    )
                else:
                    st.error("Export file could not be created or found.")
                    st.json(result)

if __name__ == "__main__":
    main()