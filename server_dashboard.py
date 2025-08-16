import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- Page Configuration ---
# Set the layout to wide mode for better visualization space
st.set_page_config(
    page_title="Health-Check Monitoring Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- Helper Function for File Reading ---
def read_file(uploaded_file):
    """Reads an uploaded file (CSV or Excel) into a pandas DataFrame."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file, engine='openpyxl')

# --- Main Application ---
st.title("📡 Health-Check Monitoring Dashboard")
st.write(
    "Upload a report to analyze server activity, or upload two reports to compare them."
)

# --- Sidebar for File Upload and Controls ---
with st.sidebar:
    st.header("⚙️ Controls")
    
    # File uploaders for new and old reports
    new_report_file = st.file_uploader(
        "Upload New Report",
        type=['xlsx', 'csv']
    )
    old_report_file = st.file_uploader(
        "Upload Old Report to Compare (Optional)",
        type=['xlsx', 'csv']
    )

    st.divider()

    # Slider to let the user define the inactivity threshold
    days_threshold = st.slider(
        "Inactive Threshold (Days)",
        min_value=1,
        max_value=120,
        value=30,  # Default to 30 days
        help="A server is considered 'inactive' if its last registration is older than this many days."
    )

# --- Main Panel for Data Display and Visualization ---
if new_report_file is not None:
    try:
        # --- Report Comparison Logic ---
        if old_report_file is not None:
            st.header("🔬 Report Comparison")
            
            df_new = read_file(new_report_file)
            df_old = read_file(old_report_file)
            
            # Ensure 'Host Name' column exists in both files
            if 'Host Name' in df_new.columns and 'Host Name' in df_old.columns:
                # Get unique host names from each dataframe
                new_hosts = set(df_new['Host Name'].unique())
                old_hosts = set(df_old['Host Name'].unique())
                
                # Identify added and removed hosts
                added_hosts = list(new_hosts - old_hosts)
                removed_hosts = list(old_hosts - new_hosts)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"🆕 Newly Added Hosts ({len(added_hosts)})")
                    if added_hosts:
                        st.dataframe(pd.DataFrame(added_hosts, columns=["Host Name"]), use_container_width=True)
                    else:
                        st.info("No new hosts were added.")
                
                with col2:
                    st.subheader(f"❌ Removed Hosts ({len(removed_hosts)})")
                    if removed_hosts:
                        st.dataframe(pd.DataFrame(removed_hosts, columns=["Host Name"]), use_container_width=True)
                    else:
                        st.info("No hosts were removed.")
            else:
                st.error("The 'Host Name' column must be present in both files to perform a comparison.")

        # --- Single File Analysis ---
        st.header("📄 Single Report Analysis")
        df = read_file(new_report_file)

        # --- Data Validation ---
        required_columns = [
            'Host Name', 'Network Location (from client)', 'Network Location (from server)',
            'Valid Key', 'Using TLS', 'Send State', 'Receive State', 'Status',
            'Registration Error', 'Last Registration', 'Version'
        ]
        
        if not all(col in df.columns for col in required_columns):
            st.error(
                "Error: The uploaded file is missing one or more required columns. "
                f"Please ensure it contains: {', '.join(required_columns)}"
            )
        else:
            # --- Data Cleaning and Preparation ---
            df['Last Registration'] = pd.to_datetime(df['Last Registration'], errors='coerce')
            original_rows = len(df)
            df.dropna(subset=['Last Registration'], inplace=True)
            if len(df) < original_rows:
                st.warning(
                    f"Warning: Dropped {original_rows - len(df)} rows due to invalid "
                    "date formats in the 'Last Registration' column."
                )

            st.success(f"✅ Successfully loaded and processed **{len(df)}** records from the new report.")
            
            # --- Inactive Server Analysis ---
            st.subheader(f"🖥️ Host Activity Analysis (Inactive for > {days_threshold} days)")
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            inactive_hosts_df = df[df['Last Registration'] < cutoff_date]
            active_hosts_df = df[df['Last Registration'] >= cutoff_date]

            st.write(f"**🔴 Inactive Hosts ({len(inactive_hosts_df)})**")
            if inactive_hosts_df.empty:
                st.info("All hosts have reported within the selected time frame.")
            else:
                st.dataframe(inactive_hosts_df)
            
            st.write(f"**🟢 Active Hosts ({len(active_hosts_df)})**")
            st.dataframe(active_hosts_df)
            
            # --- Data Visualizations ---
            st.header("📊 Data Visualizations (Based on Active Hosts)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Distribution by Status")
                fig_status = px.pie(active_hosts_df, names='Status', title='Active Host Status', hole=0.3)
                st.plotly_chart(fig_status, use_container_width=True)

                st.subheader("Distribution by Version")
                version_counts = active_hosts_df['Version'].value_counts().reset_index()
                fig_versions = px.bar(version_counts, x='Version', y='count', title='Active Host Client Versions', text_auto=True)
                st.plotly_chart(fig_versions, use_container_width=True)

            with col2:
                st.subheader("Security: TLS Usage")
                fig_tls = px.pie(active_hosts_df, names='Using TLS', title='Hosts Using TLS', hole=0.3)
                st.plotly_chart(fig_tls, use_container_width=True)
                
                st.subheader("Network Location (Client-Side)")
                net_client_counts = active_hosts_df['Network Location (from client)'].value_counts().reset_index()
                fig_net_client = px.bar(net_client_counts, x='Network Location (from client)', y='count', title='Client-Reported Network Locations', text_auto=True)
                st.plotly_chart(fig_net_client, use_container_width=True)

            # --- NEW VISUALIZATIONS ---
            st.header("🔍 Additional Analysis")
            col3, col4 = st.columns(2)

            with col3:
                # Registration Error Analysis
                st.subheader("Top Registration Errors")
                error_df = active_hosts_df[active_hosts_df['Registration Error'].notna() & (active_hosts_df['Registration Error'] != 'None')]
                if not error_df.empty:
                    error_counts = error_df['Registration Error'].value_counts().reset_index()
                    fig_errors = px.bar(error_counts, x='Registration Error', y='count', title='Common Registration Errors')
                    st.plotly_chart(fig_errors, use_container_width=True)
                else:
                    st.info("No registration errors found in active hosts.")

            with col4:
                # Network Location Mismatch Analysis
                st.subheader("Network Location Mismatches")
                mismatch_df = active_hosts_df[active_hosts_df['Network Location (from client)'] != active_hosts_df['Network Location (from server)']]
                if not mismatch_df.empty:
                    st.dataframe(mismatch_df[['Host Name', 'Network Location (from client)', 'Network Location (from server)']], use_container_width=True)
                else:
                    st.info("No network location mismatches found.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")

else:
    st.info("Awaiting file upload...")

