import streamlit as st

from utils import (
    get_filters,
    filter_data,
    compute_kpis,
    load_providers_from_df,
    load_receivers_from_df,
    load_food_listings_from_df,
    load_claims_from_df,
    merge_datasets,
    aggregate_by_city,
    get_db_connection,
    load_all_from_db,
    write_df_to_table,
    insert_record,
    update_record,
    delete_record,
    table_has_rows,
)
from charts import plot_bar, plot_pie
import os
import pandas as pd


st.set_page_config(layout="wide", page_title="Food Donation Dashboard")

# Load custom UI stylesheet (glassmorphism + eco-theme)
css_path = os.path.join('assets', 'ui.css')
if os.path.exists(css_path):
        with open(css_path, 'r') as _f:
                st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# Hero header + ornament background (presentation-ready)
hero_html = '''
<div class="bg-ornament"></div>
<div class="hero">
    <div class="hero-text">
        <h1>Food Waste Management — Sustainability Dashboard</h1>
        <p>Real-time insights into donations, claims, and environmental impact. Track meals saved, CO₂ prevented, and community reach.</p>
    </div>
    <div style="width:240px;opacity:0.95">
        <!-- Decorative SVG illustration -->
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
            <defs>
                <linearGradient id="g1" x1="0" x2="1">
                    <stop offset="0%" stop-color="#F97316" stop-opacity="0.95"/>
                    <stop offset="100%" stop-color="#38BDF8" stop-opacity="0.95"/>
                </linearGradient>
            </defs>
            <rect width="200" height="200" rx="20" fill="url(#g1)" opacity="0.10"/>
            <g transform="translate(20,40) scale(0.8)">
                <path d="M10 80c20-60 120-60 140 0" stroke="#FF8C42" stroke-width="6" fill="none" stroke-linecap="round"/>
                <circle cx="40" cy="40" r="18" fill="#F97316"/>
                <rect x="80" y="30" width="36" height="36" rx="8" fill="#38BDF8"/>
                <!-- food basket icon -->
                <g transform="translate(0,90)">
                  <path d="M30 10 q20 30 60 0" stroke="#fff" stroke-width="2" fill="none" opacity="0.08"/>
                </g>
            </g>
        </svg>
    </div>
</div>
'''
st.markdown(hero_html, unsafe_allow_html=True)

db_path = os.environ.get('SQLITE_DB_PATH', os.path.join('data', 'food_donation.db'))
table_map = {'providers':'providers','receivers':'receivers','food':'food_listings','claims':'claims'}

# Attempt to load from DB automatically
df = None
providers = None
receivers = None
claims = None
food = None
conn = get_db_connection(db_path=db_path)
if conn is None:
    st.error(f'Failed to open SQLite database at {db_path}.')
    st.stop()
try:
    # Seed SQLite from bundled CSV files only when a table is empty.
    local_map = {'providers': 'providers.csv', 'receivers': 'receivers.csv', 'food': 'food_listings.csv', 'claims': 'claims.csv'}
    for key, fname in local_map.items():
        path = os.path.join('data', fname)
        table_name = table_map.get(key, key)
        if table_has_rows(conn, table_name):
            continue
        if os.path.exists(path):
            try:
                df_src = pd.read_csv(path)
            except Exception as e:
                st.warning(f'Unable to read {path}: {e}')
                continue
            if key == 'providers':
                df_src = load_providers_from_df(df_src)
            elif key == 'receivers':
                df_src = load_receivers_from_df(df_src)
            elif key == 'food':
                df_src = load_food_listings_from_df(df_src)
            elif key == 'claims':
                df_src = load_claims_from_df(df_src)
            ok, msg = write_df_to_table(conn, df_src, table_name, truncate=False)
            if not ok:
                st.warning(f'Failed to write {path} into table {table_name}: {msg}')

    providers, receivers, food, claims = load_all_from_db(conn, table_map=table_map)
finally:
    try:
        conn.close()
    except Exception:
        pass

if food is None:
    st.error('No food listings table found or table is empty after loading CSVs. Check your data files and database schema.')
    st.stop()
df = merge_datasets(providers=providers, receivers=receivers, food=food, claims=claims)

crud_feedback = st.session_state.pop('crud_feedback', None)
if crud_feedback:
    st.success(crud_feedback)


def find_col(df, variants):
    for v in variants:
        if v in df.columns:
            return v
    return None


def render_add_section():
    a1, a2 = st.columns(2)
    with a1:
        with st.expander('Add Donation', expanded=True):
            with st.form('form_add_donation'):
                st.write('Add Donation (food_listings)')
                f_food_id = st.text_input('Food_ID', key='add_food_id')
                f_food_name = st.text_input('Food_Name', key='add_food_name')
                f_provider_id = st.text_input('Provider_ID', key='add_provider_id')
                f_qty = st.number_input('Quantity', min_value=0, value=1, key='add_qty')
                f_city = st.text_input('City', key='add_city')
                f_expiry = st.text_input('Expiry_Date (YYYY-MM-DD)', key='add_expiry')
                f_food_type = st.text_input('Food_Type', key='add_food_type')
                f_meal_type = st.text_input('Meal_Type', key='add_meal_type')
                submit = st.form_submit_button('Insert Donation')
                if submit:
                    errors = []
                    if not f_food_id:
                        errors.append('Food_ID is required')
                    else:
                        try:
                            int(f_food_id)
                        except Exception:
                            errors.append('Food_ID must be an integer')
                    if f_provider_id:
                        try:
                            pid = int(f_provider_id)
                            if providers is not None and 'Provider_ID' in providers.columns:
                                if not (providers['Provider_ID'].astype(str) == str(pid)).any():
                                    errors.append('Provider_ID not found')
                        except Exception:
                            errors.append('Provider_ID must be integer')
                    else:
                        errors.append('Provider_ID is required')
                    if f_qty <= 0:
                        errors.append('Quantity must be > 0')
                    if not f_city:
                        errors.append('City is required')
                    if f_expiry:
                        try:
                            pd.to_datetime(f_expiry)
                        except Exception:
                            errors.append('Expiry_Date must be YYYY-MM-DD')
                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            rec = {'Food_ID': f_food_id or None, 'Food_Name': f_food_name or None, 'Provider_ID': f_provider_id or None, 'Quantity': f_qty, 'City': f_city or None}
                            if f_expiry:
                                rec['Expiry_Date'] = f_expiry
                            if f_food_type:
                                rec['Food_Type'] = f_food_type
                            if f_meal_type:
                                rec['Meal_Type'] = f_meal_type
                            ok, msg = insert_record(conn, table_map.get('food','food_listings'), rec)
                            if ok:
                                refresh_after_crud('Inserted donation')
                            else:
                                st.error(f'Insert failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    with a2:
        with st.expander('Add Claim', expanded=True):
            with st.form('form_add_claim'):
                st.write('Create Claim')
                c_food_id = st.text_input('Food_ID for claim', key='add_claim_food')
                c_receiver_id = st.text_input('Receiver_ID', key='add_claim_recv')
                c_status = st.selectbox('Status', options=['pending', 'completed', 'claimed', 'cancelled'], key='add_claim_status')
                c_timestamp = st.text_input('Timestamp (YYYY-MM-DD HH:MM:SS)', key='add_claim_ts')
                submit = st.form_submit_button('Create Claim')
                if submit:
                    errors = []
                    if not c_food_id:
                        errors.append('Food_ID is required')
                    else:
                        try:
                            fid = int(c_food_id)
                            if food is not None and 'Food_ID' in food.columns:
                                if not (food['Food_ID'].astype(str) == str(fid)).any():
                                    errors.append('Food_ID not found')
                        except Exception:
                            errors.append('Food_ID must be integer')
                    if not c_receiver_id:
                        errors.append('Receiver_ID is required')
                    else:
                        try:
                            rid = int(c_receiver_id)
                            if receivers is not None and 'Receiver_ID' in receivers.columns:
                                if not (receivers['Receiver_ID'].astype(str) == str(rid)).any():
                                    errors.append('Receiver_ID not found')
                        except Exception:
                            errors.append('Receiver_ID must be integer')
                    if c_timestamp:
                        try:
                            pd.to_datetime(c_timestamp)
                        except Exception:
                            errors.append('Timestamp must be YYYY-MM-DD HH:MM:SS')
                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            rec = {'Food_ID': c_food_id or None, 'Receiver_ID': c_receiver_id or None, 'Status': c_status}
                            if c_timestamp:
                                rec['Timestamp'] = c_timestamp
                            ok, msg = insert_record(conn, table_map.get('claims','claims'), rec)
                            if ok:
                                refresh_after_crud('Claim created')
                            else:
                                st.error(f'Create failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    # Providers / Receivers add
    pr1, pr2 = st.columns(2)
    with pr1:
        with st.expander('Add Provider', expanded=True):
            with st.form('form_add_provider'):
                pid = st.text_input('Provider_ID', key='add_pid')
                name = st.text_input('Name', key='add_pname')
                ptype = st.text_input('Type', key='add_ptype')
                addr = st.text_input('Address', key='add_paddr')
                city = st.text_input('City', key='add_pcity')
                contact = st.text_input('Contact', key='add_pcontact')
                submit = st.form_submit_button('Insert Provider')
                if submit:
                    errs = []
                    if not pid:
                        errs.append('Provider_ID required')
                    else:
                        try:
                            int(pid)
                        except Exception:
                            errs.append('Provider_ID integer')
                    if not name:
                        errs.append('Name required')
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            rec = {'Provider_ID': pid, 'ProviderName': name, 'Type': ptype, 'Address': addr, 'City': city, 'Contact': contact}
                            ok, msg = insert_record(conn, table_map.get('providers','providers'), rec)
                            if ok:
                                refresh_after_crud('Provider added')
                            else:
                                st.error(f'Insert failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    with pr2:
        with st.expander('Add Receiver', expanded=True):
            with st.form('form_add_receiver'):
                rid = st.text_input('Receiver_ID', key='add_rid')
                rname = st.text_input('Name', key='add_rname')
                rtype = st.text_input('Type', key='add_rtype')
                rcity = st.text_input('City', key='add_rcity')
                rcontact = st.text_input('Contact', key='add_rcontact')
                submit = st.form_submit_button('Insert Receiver')
                if submit:
                    errs = []
                    if not rid:
                        errs.append('Receiver_ID required')
                    else:
                        try:
                            int(rid)
                        except Exception:
                            errs.append('Receiver_ID integer')
                    if not rname:
                        errs.append('Name required')
                    if errs:
                        for e in errs:
                            st.error(e)
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            rec = {'Receiver_ID': rid, 'Name': rname, 'Type': rtype, 'City': rcity, 'Contact': rcontact}
                            ok, msg = insert_record(conn, table_map.get('receivers','receivers'), rec)
                            if ok:
                                refresh_after_crud('Receiver added')
                            else:
                                st.error(f'Insert failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass


def render_update_section():
    u1, u2 = st.columns(2)
    with u1:
        with st.expander('Update Donation', expanded=True):
            st.write('Update Donation fields (select Food)')
            food_opts = []
            food_ids = []
            if food is not None and 'Food_ID' in food.columns:
                for _, r in food.iterrows():
                    label = f"{r.get('Food_Name', '')} (ID:{r.get('Food_ID')})" if 'Food_Name' in food.columns else str(r.get('Food_ID'))
                    food_opts.append(label)
                    food_ids.append(str(r.get('Food_ID')))
            sel = st.selectbox('Select Food', options=[''] + food_opts, key='upd_food_sel')
            if sel:
                idx = food_opts.index(sel)
                sel_id = food_ids[idx]
                with st.form('form_update_donation'):
                    uf_name = st.text_input('Food_Name', key='upd_food_name')
                    uf_qty = st.number_input('Quantity', min_value=0, value=0, key='upd_food_qty')
                    uf_expiry = st.text_input('Expiry_Date (YYYY-MM-DD)', key='upd_food_expiry')
                    submit = st.form_submit_button('Update Donation')
                    if submit:
                        updates = {}
                        if uf_name:
                            updates['Food_Name'] = uf_name
                        if uf_qty and uf_qty > 0:
                            updates['Quantity'] = uf_qty
                        if uf_expiry:
                            try:
                                pd.to_datetime(uf_expiry)
                                updates['Expiry_Date'] = uf_expiry
                            except Exception:
                                st.error('Expiry_Date must be YYYY-MM-DD')
                        if not updates:
                            st.error('No updates provided')
                        else:
                            conn = get_db_connection(db_path=db_path)
                            if conn is None:
                                st.error('DB connection failed')
                            else:
                                ok, msg = update_record(conn, table_map.get('food','food_listings'), 'Food_ID', sel_id, updates)
                                if ok:
                                    refresh_after_crud('Donation updated')
                                else:
                                    st.error(f'Update failed: {msg}')
                                try:
                                    conn.close()
                                except Exception:
                                    pass

    with u2:
        with st.expander('Update Claim', expanded=True):
            st.write('Update Claim Status')
            claim_opts = []
            claim_ids = []
            if claims is not None and 'Claim_ID' in claims.columns:
                for _, r in claims.iterrows():
                    label = f"Claim {r.get('Claim_ID')} - Food {r.get('Food_ID')} - Receiver {r.get('Receiver_ID')}"
                    claim_opts.append(label)
                    claim_ids.append(str(r.get('Claim_ID')))
            selc = st.selectbox('Select Claim', options=[''] + claim_opts, key='upd_claim_sel')
            new_status = st.selectbox('New Status', options=['pending', 'completed', 'claimed', 'cancelled'], key='upd_claim_status')
            with st.form('form_update_claim'):
                submit = st.form_submit_button('Update Claim')
                if submit:
                    if not selc:
                        st.error('Select a Claim')
                    else:
                        idx = claim_opts.index(selc)
                        claim_id = claim_ids[idx]
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = update_record(conn, table_map.get('claims','claims'), 'Claim_ID', claim_id, {'Status': new_status})
                            if ok:
                                refresh_after_crud('Claim updated')
                            else:
                                st.error(f'Update failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    # Providers / Receivers update
    ur1, ur2 = st.columns(2)
    with ur1:
        with st.expander('Update Provider', expanded=True):
            prov_opts = []
            prov_ids = []
            if providers is not None and 'Provider_ID' in providers.columns:
                for _, r in providers.iterrows():
                    prov_opts.append(str(r.get('ProviderName')))
                    prov_ids.append(str(r.get('Provider_ID')))
            selp = st.selectbox('Select Provider', options=[''] + prov_opts, key='upd_prov_sel')
            new_name = st.text_input('New Name', key='upd_prov_name')
            new_city = st.text_input('New City', key='upd_prov_city')
            if st.button('Update Provider', key='update_provider'):
                if not selp:
                    st.error('Select a Provider')
                else:
                    idx = prov_opts.index(selp)
                    sel_id = prov_ids[idx]
                    updates = {}
                    if new_name:
                        updates['ProviderName'] = new_name
                    if new_city:
                        updates['City'] = new_city
                    if not updates:
                        st.error('No updates provided')
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = update_record(conn, table_map.get('providers','providers'), 'Provider_ID', sel_id, updates)
                            if ok:
                                refresh_after_crud('Provider updated')
                            else:
                                st.error(f'Update failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    with ur2:
        with st.expander('Update Receiver', expanded=True):
            recv_opts = []
            recv_ids = []
            if receivers is not None and 'Receiver_ID' in receivers.columns:
                for _, r in receivers.iterrows():
                    recv_opts.append(str(r.get('Name')))
                    recv_ids.append(str(r.get('Receiver_ID')))
            selr = st.selectbox('Select Receiver', options=[''] + recv_opts, key='upd_recv_sel')
            rnew_name = st.text_input('New Name', key='upd_recv_name')
            rnew_city = st.text_input('New City', key='upd_recv_city')
            if st.button('Update Receiver', key='update_receiver'):
                if not selr:
                    st.error('Select a Receiver')
                else:
                    idx = recv_opts.index(selr)
                    sel_id = recv_ids[idx]
                    updates = {}
                    if rnew_name:
                        updates['Name'] = rnew_name
                    if rnew_city:
                        updates['City'] = rnew_city
                    if not updates:
                        st.error('No updates provided')
                    else:
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = update_record(conn, table_map.get('receivers','receivers'), 'Receiver_ID', sel_id, updates)
                            if ok:
                                refresh_after_crud('Receiver updated')
                            else:
                                st.error(f'Update failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass


def render_delete_section():
    d1, d2 = st.columns(2)
    with d1:
        with st.expander('Delete Donation', expanded=True):
            st.write('Delete donation by Food')
            food_opts = []
            food_ids = []
            if food is not None and 'Food_ID' in food.columns:
                for _, r in food.iterrows():
                    label = f"{r.get('Food_Name', '')} (ID:{r.get('Food_ID')})" if 'Food_Name' in food.columns else str(r.get('Food_ID'))
                    food_opts.append(label)
                    food_ids.append(str(r.get('Food_ID')))
            self = st.selectbox('Select Food to delete', options=[''] + food_opts, key='del_food_sel')
            with st.form('form_delete_donation'):
                submit = st.form_submit_button('Delete Donation')
                if submit:
                    if not self:
                        st.error('Select a Food')
                    else:
                        idx = food_opts.index(self)
                        sel_id = food_ids[idx]
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = delete_record(conn, table_map.get('food','food_listings'), 'Food_ID', sel_id)
                            if ok:
                                refresh_after_crud('Donation deleted')
                            else:
                                st.error(f'Delete failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

        with st.expander('Delete Claim', expanded=True):
            st.write('Delete claim by Claim')
            claim_opts = []
            claim_ids = []
            if claims is not None and 'Claim_ID' in claims.columns:
                for _, r in claims.iterrows():
                    label = f"Claim {r.get('Claim_ID')} - Food {r.get('Food_ID')} - Receiver {r.get('Receiver_ID')}"
                    claim_opts.append(label)
                    claim_ids.append(str(r.get('Claim_ID')))
            selc = st.selectbox('Select Claim to delete', options=[''] + claim_opts, key='del_claim_sel')
            with st.form('form_delete_claim'):
                submit = st.form_submit_button('Delete Claim')
                if submit:
                    if not selc:
                        st.error('Select a Claim')
                    else:
                        idx = claim_opts.index(selc)
                        cid = claim_ids[idx]
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = delete_record(conn, table_map.get('claims','claims'), 'Claim_ID', cid)
                            if ok:
                                refresh_after_crud('Claim deleted')
                            else:
                                st.error(f'Delete failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

    with d2:
        with st.expander('Delete Provider', expanded=True):
            prov_opts = []
            prov_ids = []
            if providers is not None and 'Provider_ID' in providers.columns:
                for _, r in providers.iterrows():
                    prov_opts.append(str(r.get('ProviderName')))
                    prov_ids.append(str(r.get('Provider_ID')))
            selp = st.selectbox('Select Provider to delete', options=[''] + prov_opts, key='del_prov_sel')
            with st.form('form_delete_provider'):
                submit = st.form_submit_button('Delete Provider')
                if submit:
                    if not selp:
                        st.error('Select a Provider')
                    else:
                        idx = prov_opts.index(selp)
                        pid = prov_ids[idx]
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = delete_record(conn, table_map.get('providers','providers'), 'Provider_ID', pid)
                            if ok:
                                refresh_after_crud('Provider deleted')
                            else:
                                st.error(f'Delete failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass

        with st.expander('Delete Receiver', expanded=True):
            recv_opts = []
            recv_ids = []
            if receivers is not None and 'Receiver_ID' in receivers.columns:
                for _, r in receivers.iterrows():
                    recv_opts.append(str(r.get('Name')))
                    recv_ids.append(str(r.get('Receiver_ID')))
            selr = st.selectbox('Select Receiver to delete', options=[''] + recv_opts, key='del_recv_sel')
            with st.form('form_delete_receiver'):
                submit = st.form_submit_button('Delete Receiver')
                if submit:
                    if not selr:
                        st.error('Select a Receiver')
                    else:
                        idx = recv_opts.index(selr)
                        rid = recv_ids[idx]
                        conn = get_db_connection(db_path=db_path)
                        if conn is None:
                            st.error('DB connection failed')
                        else:
                            ok, msg = delete_record(conn, table_map.get('receivers','receivers'), 'Receiver_ID', rid)
                            if ok:
                                refresh_after_crud('Receiver deleted')
                            else:
                                st.error(f'Delete failed: {msg}')
                            try:
                                conn.close()
                            except Exception:
                                pass


# Data loaded from DB and merged above


# Sidebar controls: filters then navigation
st.sidebar.title("Controls")

# Navigation above filters for quicker access
page = st.sidebar.radio("Navigate", [
    'Overview', 'EDA', 'Bivariate', 'Multivariate', 'Claims', 'Providers', 'Query Outputs', 'Data', 'Actions'
])

filters = get_filters(df)
selected = {}
with st.sidebar.expander("Filters", expanded=True):
    for k, opts in filters.items():
        if opts['type'] == 'multi':
            selected[k] = st.multiselect(k, options=opts['options'], default=opts['options'])
        elif opts['type'] == 'date':
            selected[k] = st.date_input(k, value=(opts['min'].date(), opts['max'].date()))

filtered = filter_data(df, filters, selected)


def render_overview(df, filtered):
        st.markdown("""
        <div class='section'><div class='section-title'>Overview</div><div class='section-sub'>High-level KPIs and quick charts.</div></div>
        """, unsafe_allow_html=True)

        kpis = compute_kpis(filtered)
        # derive additional metrics without changing core data
        total_providers = providers.shape[0] if providers is not None else (filtered['Provider'].nunique() if 'Provider' in filtered.columns else 0)
        total_receivers = receivers.shape[0] if receivers is not None else (filtered['ReceiverName'].nunique() if 'ReceiverName' in filtered.columns else 0)
        active_listings = len(food) if 'food' in globals() and food is not None else (filtered['Food_ID'].nunique() if 'Food_ID' in filtered.columns else len(filtered))
        total_claims = len(claims) if 'claims' in globals() and claims is not None else (filtered['ClaimStatus'].notna().sum() if 'ClaimStatus' in filtered.columns else 0)
        meals_saved = int(kpis.get('total_quantity', 0))
        if claims is not None and 'Status' in claims.columns:
                successful_deliveries = int(claims['Status'].astype(str).str.lower().isin(['completed', 'complete', 'done', 'claimed']).sum())
        else:
                successful_deliveries = int(filtered['ClaimStatus'].astype(str).str.lower().isin(['completed', 'complete', 'done', 'claimed']).sum()) if 'ClaimStatus' in filtered.columns else 0

        # KPI grid (premium cards)
        kpi_html = f"""
        <div class='kpi-grid'>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>P</div><div><div class='kpi-title'>Total Providers</div><div class='kpi-value'>{total_providers}</div></div></div><div class='kpi-trend'>↗ 5% MoM</div></div>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>R</div><div><div class='kpi-title'>Total Receivers</div><div class='kpi-value'>{total_receivers}</div></div></div><div class='kpi-trend'>↗ 2% MoM</div></div>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>L</div><div><div class='kpi-title'>Active Listings</div><div class='kpi-value'>{active_listings}</div></div></div><div class='kpi-trend'>↘ -1% MoM</div></div>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>C</div><div><div class='kpi-title'>Total Claims</div><div class='kpi-value'>{total_claims}</div></div></div><div class='kpi-trend'>↗ {kpis.get('pct_completed',0):.1f}% completed</div></div>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>🍽️</div><div><div class='kpi-title'>Meals Saved</div><div class='kpi-value'>{meals_saved}</div></div></div><div class='kpi-trend'>Est. impact</div></div>
            <div class='kpi-card'><div style='display:flex;align-items:center;gap:12px'><div class='icon'>🚚</div><div><div class='kpi-title'>Successful Deliveries</div><div class='kpi-value'>{successful_deliveries}</div></div></div><div class='kpi-trend'>Completed claims</div></div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

        st.markdown('---')
        st.subheader('Food Availability by City')
        city_agg = aggregate_by_city(filtered)
        st.plotly_chart(plot_bar(city_agg, groupby='City', value_col='Quantity'), use_container_width=True)

        # Sustainability Impact
        co2_saved_kg = meals_saved * 0.5
        waste_prevented_kg = meals_saved * 0.6
        st.markdown("""
        <div class='section' style='display:flex;gap:18px;margin-top:18px'>
            <div style='flex:1'>
                <div class='section-title'>Sustainability Impact</div>
                <div class='kpi-grid'>
                    <div class='kpi-card'><div class='kpi-title'>CO₂ Emissions Saved (kg)</div><div class='kpi-value'>%d</div></div>
                    <div class='kpi-card'><div class='kpi-title'>Food Waste Prevented (kg)</div><div class='kpi-value'>%d</div></div>
                    <div class='kpi-card'><div class='kpi-title'>Community Impact Score</div><div class='kpi-value'>%d</div></div>
                </div>
            </div>
            <div style='width:360px'>
                <div class='section-title'>Recent Activity</div>
        """ % (int(co2_saved_kg), int(waste_prevented_kg), min(100, int(meals_saved/10))) , unsafe_allow_html=True)

        # Recent activity feed (top 6 events)
        recent = None
        if 'ClaimTimestamp' in filtered.columns:
                recent = filtered.sort_values('ClaimTimestamp', ascending=False).head(6)
        elif 'PickupDate' in filtered.columns:
                recent = filtered.sort_values('PickupDate', ascending=False).head(6)
        else:
                recent = filtered.head(6)
        for idx, row in recent.iterrows():
                note = ''
                if 'Provider' in row.index and 'Quantity' in row.index:
                        note = f"{row.get('Provider','Unknown')} → {row.get('ReceiverName','Receiver')} ({row.get('Quantity',0)})"
                else:
                        note = str(row.dropna().to_dict())
                st.markdown(f"<div class='activity-item'>{note}</div>", unsafe_allow_html=True)

        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick actions removed (UI-only non-functional elements)


def render_eda(filtered, providers, receivers):
    st.subheader('Univariate Distributions')
    provider_type_source = providers if providers is not None else filtered
    provider_type_col = find_col(provider_type_source, ['Provider_Type', 'ProviderType', 'Type', 'provider_type'])
    food_type_col = find_col(filtered, ['Food_Type', 'FoodType', 'Food Type'])
    meal_type_col = find_col(filtered, ['Meal_Type', 'MealType', 'Meal Type'])

    c1, c2 = st.columns(2)
    if provider_type_col:
        c1.plotly_chart(plot_bar(provider_type_source, groupby=provider_type_col), use_container_width=True)
    else:
        c1.info('No provider type column available')
    if food_type_col:
        c2.plotly_chart(plot_bar(filtered, groupby=food_type_col), use_container_width=True)
    else:
        c2.info('No food type column available')


def render_bivariate(filtered, providers):
    st.subheader('Bivariate Analyses')
    c1, c2 = st.columns(2)
    city_count = filtered.groupby('City').size().reset_index(name='listings').sort_values('listings', ascending=False)
    c1.plotly_chart(plot_bar(city_count, groupby='City', value_col='listings'), use_container_width=True)
    if providers is not None and 'City' in providers.columns:
        provider_city_count = providers.groupby('City').size().reset_index(name='providers').sort_values('providers', ascending=False)
        c2.plotly_chart(plot_bar(provider_city_count, groupby='City', value_col='providers'), use_container_width=True)
    else:
        c2.info('Provider city data is not available')


def render_multivariate(filtered, providers):
    st.subheader('Multivariate (Treemap)')
    import plotly.express as px

    if providers is not None and {'City', 'Type'}.issubset(providers.columns):
        provider_tree = providers[['City', 'Type']].copy()
        provider_tree['City'] = provider_tree['City'].fillna('Unknown')
        provider_tree['Type'] = provider_tree['Type'].fillna('Unknown')
        provider_tree['ProviderCount'] = 1
        provider_agg = provider_tree.groupby(['City', 'Type'], dropna=False)['ProviderCount'].sum().reset_index()
        fig = px.treemap(
            provider_agg,
            path=['City', 'Type'],
            values='ProviderCount',
            title='Provider Count by City / Provider Type',
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Provider city/type data is not available')

    prov_type_col = find_col(filtered, ['Provider_Type', 'ProviderType'])
    if 'City' in filtered.columns and prov_type_col and 'Quantity' in filtered.columns:
        treemap_df = filtered.copy()
        treemap_df['ProviderType'] = treemap_df[prov_type_col]
        treemap_agg = treemap_df.groupby(['City', 'ProviderType'])['Quantity'].sum().reset_index()
        fig = px.treemap(treemap_agg, path=['City', 'ProviderType'], values='Quantity', title='City / Provider Type / Quantity')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Not enough columns for multivariate treemap')


def render_claims(filtered):
    st.subheader('Claims Analysis')
    if 'ClaimStatus' in filtered.columns:
        st.plotly_chart(plot_pie(filtered, names_col='ClaimStatus', title='Claim Status Distribution'), use_container_width=True)
    else:
        st.info('No claim status available')
    if 'ReceiverName' in filtered.columns:
        top_recv = filtered.groupby('ReceiverName')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(10)
        st.table(top_recv)


def render_providers(filtered, providers):
    st.subheader('Provider Contact Information')
    if providers is not None:
        city_select = st.selectbox('Select city to view providers', options=sorted(providers['City'].dropna().unique()))
        provs_in_city = providers[providers['City'] == city_select][['Provider_ID', 'ProviderName', 'Contact', 'Address']]
        provs_in_city = provs_in_city.rename(columns={'ProviderName': 'Provider'})
        st.table(provs_in_city)
    else:
        if 'Provider' in filtered.columns and 'ProviderContact' in filtered.columns and 'City' in filtered.columns:
            city_select = st.selectbox('Select city to view providers (from merged data)', options=sorted(filtered['City'].dropna().unique()))
            provs = filtered[filtered['City'] == city_select][['Provider', 'ProviderContact']].drop_duplicates()
            st.table(provs)
        else:
            st.info('Provider contact info not available; upload providers CSV for full details')


def render_queries(filtered, providers, receivers, claims, food):
    st.subheader('Query Outputs (SQL-like)')
    with st.expander('Show query results'):
        if providers is not None:
            prov_by_city = providers.groupby('City').size().reset_index(name='providers')
            st.write('Providers by city')
            st.table(prov_by_city)
        if receivers is not None:
            recv_by_city = receivers.groupby('City').size().reset_index(name='receivers')
            st.write('Receivers by city')
            st.table(recv_by_city)

        if 'Provider_Type' in filtered.columns and 'Quantity' in filtered.columns:
            prov_type_sum = filtered.groupby('Provider_Type')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
            st.write('Provider type by total quantity')
            st.table(prov_type_sum)

        if 'ReceiverName' in filtered.columns:
            recv_claims = filtered.groupby('ReceiverName')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
            st.write('Receivers by claimed quantity')
            st.table(recv_claims.head(20))

        st.write('Total quantity available:')
        st.write(filtered['Quantity'].sum() if 'Quantity' in filtered.columns else 0)

        city_count = filtered.groupby('City').size().reset_index(name='listings').sort_values('listings', ascending=False)
        st.write('City with most listings (by count)')
        st.table(city_count.head(10))

        food_type_col = find_col(filtered, ['Food_Type', 'FoodType', 'Food Type'])
        if food_type_col:
            food_counts = filtered[food_type_col].value_counts().reset_index()
            food_counts.columns = [food_type_col, 'count']
            st.write('Most common food types')
            st.table(food_counts.head(10))

        if claims is not None:
            claims_per_food = claims.groupby('Food_ID').size().reset_index(name='claims').sort_values('claims', ascending=False)
            st.write('Claims per food item')
            st.table(claims_per_food.head(20))

        if claims is not None and 'Status' in claims.columns and 'Food_ID' in claims.columns and providers is not None:
            successful = claims[claims['Status'].astype(str).str.lower().isin(['completed', 'complete', 'done', 'claimed'])]
            merged = successful.merge(food[['Food_ID', 'Provider_ID']], on='Food_ID', how='left')
            merged = merged.merge(providers[['Provider_ID', 'ProviderName']], on='Provider_ID', how='left')
            prov_success = merged.groupby('ProviderName').size().reset_index(name='successful_claims').sort_values('successful_claims', ascending=False)
            st.write('Providers by successful claims')
            st.table(prov_success.head(10))

        if 'ClaimStatus' in filtered.columns:
            status_counts = filtered['ClaimStatus'].value_counts(normalize=True).mul(100).reset_index()
            status_counts.columns = ['Status', 'pct']
            st.write('Claim status %')
            st.table(status_counts)

        if 'ReceiverName' in filtered.columns and 'Quantity' in filtered.columns:
            avg_claim_per_recv = filtered.groupby('ReceiverName')['Quantity'].mean().reset_index().sort_values('Quantity', ascending=False)
            st.write('Average quantity claimed per receiver')
            st.table(avg_claim_per_recv.head(20))

        meal_type_col = find_col(filtered, ['Meal_Type', 'MealType', 'Meal Type'])
        if meal_type_col and 'Quantity' in filtered.columns:
            meal_claims = filtered.groupby(meal_type_col)['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
            st.write('Meal types by claimed quantity')
            st.table(meal_claims)

        if 'Provider' in filtered.columns and 'Quantity' in filtered.columns:
            st.write('Total quantity donated by provider')
            st.table(filtered.groupby('Provider')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(20))


def render_data(filtered):
    st.subheader('Filtered Data')
    st.dataframe(filtered)
    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button(label="Download filtered data", data=csv, file_name='filtered.csv', mime='text/csv')


def open_modal(entity, action):
    st.session_state['modal_open'] = True
    st.session_state['modal_entity'] = entity
    st.session_state['modal_action'] = action


def close_modal():
    st.session_state['modal_open'] = False
    st.session_state['modal_entity'] = None
    st.session_state['modal_action'] = None


def refresh_after_crud(message):
    st.session_state['crud_feedback'] = message
    close_modal()
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()


def _next_numeric_id(df, col):
    """Suggest the next integer ID for a table (max existing + 1)."""
    try:
        if df is not None and col in df.columns and len(df) > 0:
            mx = pd.to_numeric(df[col], errors='coerce').max()
            if pd.notna(mx):
                return int(mx) + 1
    except Exception:
        pass
    return 1


def _select_options(df, id_col, label_cols):
    """Build (labels, ids) for a selectbox that shows human-readable names."""
    labels, ids = [], []
    if df is not None and id_col in df.columns:
        for _, r in df.iterrows():
            parts = [str(r.get(c)) for c in label_cols
                     if c in df.columns and pd.notna(r.get(c)) and str(r.get(c)).strip()]
            name = ' · '.join(parts) if parts else f'ID {r.get(id_col)}'
            labels.append(f'{name}  (#{r.get(id_col)})')
            ids.append(str(r.get(id_col)))
    return labels, ids


def _distinct_values(df, col):
    """Sorted distinct non-empty values of a column, for friendly dropdowns."""
    if df is not None and col in df.columns:
        return sorted({str(v) for v in df[col].dropna() if str(v).strip()})
    return []


def render_action_modal(providers, receivers, food, claims):
    if not st.session_state.get('modal_open'):
        return
    entity = st.session_state.get('modal_entity')
    action = st.session_state.get('modal_action')
    title = f"{action} {entity}"
    use_modal = hasattr(st, 'modal')
    ctx = st.modal(title) if use_modal else st.expander(title, expanded=True)
    with ctx:
        form_key = f"form_{entity}_{action}"
        with st.form(form_key):
            # Build forms per entity/action
            if entity == 'Food':
                if action == 'Add':
                    new_fid = _next_numeric_id(food, 'Food_ID')
                    st.caption(f'New Food ID will be assigned automatically: #{new_fid}')
                    fname = st.text_input('Food name')
                    prov_labels, prov_ids = _select_options(providers, 'Provider_ID', ['ProviderName', 'City'])
                    prov_choice = st.selectbox('Provider', options=[''] + prov_labels)
                    qty = st.number_input('Quantity', min_value=0, value=1)
                    city = st.text_input('City')
                    food_types = _distinct_values(food, 'Food_Type')
                    meal_types = _distinct_values(food, 'Meal_Type')
                    ftype = st.selectbox('Food type', options=food_types) if food_types else st.text_input('Food type')
                    mtype = st.selectbox('Meal type', options=meal_types) if meal_types else st.text_input('Meal type')
                    expiry = st.date_input('Expiry date')
                    submit = st.form_submit_button('Insert')
                    if submit:
                        errors = []
                        if not fname:
                            errors.append('Food name is required')
                        if not prov_choice:
                            errors.append('Please choose a Provider')
                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            pid = prov_ids[prov_labels.index(prov_choice)]
                            conn = get_db_connection(db_path=db_path)
                            rec = {'Food_ID': new_fid, 'Food_Name': fname, 'Provider_ID': pid, 'Quantity': qty, 'City': city}
                            if ftype:
                                rec['Food_Type'] = ftype
                            if mtype:
                                rec['Meal_Type'] = mtype
                            if expiry:
                                rec['Expiry_Date'] = str(expiry)
                            ok, msg = insert_record(conn, table_map.get('food','food_listings'), rec)
                            if ok:
                                refresh_after_crud(f'Food listing added (#{new_fid})')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

                elif action == 'Update':
                    food_opts = []
                    food_ids = []
                    if food is not None and 'Food_ID' in food.columns:
                        for _, r in food.iterrows():
                            label = f"{r.get('Food_Name','')} (ID:{r.get('Food_ID')})"
                            food_opts.append(label)
                            food_ids.append(str(r.get('Food_ID')))
                    sel = st.selectbox('Select Food', options=[''] + food_opts)
                    new_name = st.text_input('Food_Name')
                    new_qty = st.number_input('Quantity', min_value=0, value=0)
                    submit = st.form_submit_button('Update')
                    if submit:
                        if not sel:
                            st.error('Select an item')
                        else:
                            idx = food_opts.index(sel)
                            fid = food_ids[idx]
                            updates = {}
                            if new_name:
                                updates['Food_Name'] = new_name
                            if new_qty and new_qty > 0:
                                updates['Quantity'] = new_qty
                            if updates:
                                conn = get_db_connection(db_path=db_path)
                                ok, msg = update_record(conn, table_map.get('food','food_listings'), 'Food_ID', fid, updates)
                                if ok:
                                    refresh_after_crud('Food listing updated')
                                else:
                                    st.error(msg)
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                            else:
                                st.error('No updates provided')

                else:  # Delete
                    food_opts = []
                    food_ids = []
                    if food is not None and 'Food_ID' in food.columns:
                        for _, r in food.iterrows():
                            label = f"{r.get('Food_Name','')} (ID:{r.get('Food_ID')})"
                            food_opts.append(label)
                            food_ids.append(str(r.get('Food_ID')))
                    sel = st.selectbox('Select Food to delete', options=[''] + food_opts)
                    submit = st.form_submit_button('Delete')
                    if submit:
                        if not sel:
                            st.error('Select an item')
                        else:
                            idx = food_opts.index(sel)
                            fid = food_ids[idx]
                            conn = get_db_connection(db_path=db_path)
                            ok, msg = delete_record(conn, table_map.get('food','food_listings'), 'Food_ID', fid)
                            if ok:
                                refresh_after_crud('Food listing deleted')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

            elif entity == 'Claims':
                if action == 'Add':
                    new_cid = _next_numeric_id(claims, 'Claim_ID')
                    st.caption(f'New Claim ID will be assigned automatically: #{new_cid}')
                    food_labels, food_ids = _select_options(food, 'Food_ID', ['Food_Name', 'City'])
                    recv_labels, recv_ids = _select_options(receivers, 'Receiver_ID', ['Name', 'City'])
                    food_choice = st.selectbox('Food listing', options=[''] + food_labels)
                    recv_choice = st.selectbox('Receiver', options=[''] + recv_labels)
                    status = st.selectbox('Status', options=['pending','completed','claimed','cancelled'])
                    submit = st.form_submit_button('Create')
                    if submit:
                        errors = []
                        if not food_choice:
                            errors.append('Please choose a Food listing')
                        if not recv_choice:
                            errors.append('Please choose a Receiver')
                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            fid = food_ids[food_labels.index(food_choice)]
                            rid = recv_ids[recv_labels.index(recv_choice)]
                            conn = get_db_connection(db_path=db_path)
                            rec = {'Claim_ID': new_cid, 'Food_ID': fid, 'Receiver_ID': rid, 'Status': status,
                                   'Timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                            ok, msg = insert_record(conn, table_map.get('claims','claims'), rec)
                            if ok:
                                refresh_after_crud(f'Claim created (#{new_cid})')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

                elif action == 'Update':
                    claim_opts = []
                    claim_ids = []
                    if claims is not None and 'Claim_ID' in claims.columns:
                        for _, r in claims.iterrows():
                            label = f"Claim {r.get('Claim_ID')} - Food {r.get('Food_ID')}"
                            claim_opts.append(label)
                            claim_ids.append(str(r.get('Claim_ID')))
                    sel = st.selectbox('Select Claim', options=[''] + claim_opts)
                    new_status = st.selectbox('New Status', options=['pending','completed','claimed','cancelled'])
                    submit = st.form_submit_button('Update')
                    if submit:
                        if not sel:
                            st.error('Select a claim')
                        else:
                            idx = claim_opts.index(sel)
                            cid = claim_ids[idx]
                            conn = get_db_connection(db_path=db_path)
                            ok, msg = update_record(conn, table_map.get('claims','claims'), 'Claim_ID', cid, {'Status': new_status})
                            if ok:
                                refresh_after_crud('Claim updated')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

                else:  # Delete
                    claim_opts = []
                    claim_ids = []
                    if claims is not None and 'Claim_ID' in claims.columns:
                        for _, r in claims.iterrows():
                            label = f"Claim {r.get('Claim_ID')} - Food {r.get('Food_ID')}"
                            claim_opts.append(label)
                            claim_ids.append(str(r.get('Claim_ID')))
                    sel = st.selectbox('Select Claim to delete', options=[''] + claim_opts)
                    submit = st.form_submit_button('Delete')
                    if submit:
                        if not sel:
                            st.error('Select a claim')
                        else:
                            idx = claim_opts.index(sel)
                            cid = claim_ids[idx]
                            conn = get_db_connection(db_path=db_path)
                            ok, msg = delete_record(conn, table_map.get('claims','claims'), 'Claim_ID', cid)
                            if ok:
                                refresh_after_crud('Claim deleted')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

            elif entity == 'Providers':
                if action == 'Add':
                    new_pid = _next_numeric_id(providers, 'Provider_ID')
                    st.caption(f'New Provider ID will be assigned automatically: #{new_pid}')
                    name = st.text_input('Provider name')
                    prov_types = _distinct_values(providers, 'Type')
                    ptype = st.selectbox('Type', options=prov_types) if prov_types else st.text_input('Type')
                    addr = st.text_input('Address')
                    city = st.text_input('City')
                    contact = st.text_input('Contact')
                    submit = st.form_submit_button('Insert')
                    if submit:
                        if not name:
                            st.error('Provider name is required')
                        else:
                            conn = get_db_connection(db_path=db_path)
                            rec = {'Provider_ID': new_pid, 'ProviderName': name, 'Type': ptype, 'Address': addr, 'City': city, 'Contact': contact}
                            ok, msg = insert_record(conn, table_map.get('providers','providers'), rec)
                            if ok:
                                refresh_after_crud(f'Provider added (#{new_pid})')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

                elif action == 'Update':
                    prov_opts = []
                    prov_ids = []
                    if providers is not None and 'Provider_ID' in providers.columns:
                        for _, r in providers.iterrows():
                            prov_opts.append(str(r.get('ProviderName')))
                            prov_ids.append(str(r.get('Provider_ID')))
                    sel = st.selectbox('Select Provider', options=[''] + prov_opts)
                    new_name = st.text_input('New Name')
                    new_city = st.text_input('New City')
                    submit = st.form_submit_button('Update')
                    if submit:
                        if not sel:
                            st.error('Select a provider')
                        else:
                            idx = prov_opts.index(sel)
                            pid = prov_ids[idx]
                            updates = {}
                            if new_name:
                                updates['ProviderName'] = new_name
                            if new_city:
                                updates['City'] = new_city
                            if updates:
                                conn = get_db_connection(db_path=db_path)
                                ok, msg = update_record(conn, table_map.get('providers','providers'), 'Provider_ID', pid, updates)
                                if ok:
                                    refresh_after_crud('Provider updated')
                                else:
                                    st.error(msg)
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                            else:
                                st.error('No updates provided')

                else:  # Delete
                    prov_opts = []
                    prov_ids = []
                    if providers is not None and 'Provider_ID' in providers.columns:
                        for _, r in providers.iterrows():
                            prov_opts.append(str(r.get('ProviderName')))
                            prov_ids.append(str(r.get('Provider_ID')))
                    sel = st.selectbox('Select Provider to delete', options=[''] + prov_opts)
                    submit = st.form_submit_button('Delete')
                    if submit:
                        if not sel:
                            st.error('Select a provider')
                        else:
                            idx = prov_opts.index(sel)
                            pid = prov_ids[idx]
                            conn = get_db_connection(db_path=db_path)
                            ok, msg = delete_record(conn, table_map.get('providers','providers'), 'Provider_ID', pid)
                            if ok:
                                refresh_after_crud('Provider deleted')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

            elif entity == 'Receivers':
                if action == 'Add':
                    new_rid = _next_numeric_id(receivers, 'Receiver_ID')
                    st.caption(f'New Receiver ID will be assigned automatically: #{new_rid}')
                    name = st.text_input('Receiver name')
                    recv_types = _distinct_values(receivers, 'Type')
                    rtype = st.selectbox('Type', options=recv_types) if recv_types else st.text_input('Type')
                    city = st.text_input('City')
                    contact = st.text_input('Contact')
                    submit = st.form_submit_button('Insert')
                    if submit:
                        if not name:
                            st.error('Receiver name is required')
                        else:
                            conn = get_db_connection(db_path=db_path)
                            rec = {'Receiver_ID': new_rid, 'Name': name, 'Type': rtype, 'City': city, 'Contact': contact}
                            ok, msg = insert_record(conn, table_map.get('receivers','receivers'), rec)
                            if ok:
                                refresh_after_crud(f'Receiver added (#{new_rid})')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass

                elif action == 'Update':
                    recv_opts = []
                    recv_ids = []
                    if receivers is not None and 'Receiver_ID' in receivers.columns:
                        for _, r in receivers.iterrows():
                            recv_opts.append(str(r.get('Name')))
                            recv_ids.append(str(r.get('Receiver_ID')))
                    sel = st.selectbox('Select Receiver', options=[''] + recv_opts)
                    new_name = st.text_input('New Name')
                    new_city = st.text_input('New City')
                    submit = st.form_submit_button('Update')
                    if submit:
                        if not sel:
                            st.error('Select a receiver')
                        else:
                            idx = recv_opts.index(sel)
                            rid = recv_ids[idx]
                            updates = {}
                            if new_name:
                                updates['Name'] = new_name
                            if new_city:
                                updates['City'] = new_city
                            if updates:
                                conn = get_db_connection(db_path=db_path)
                                ok, msg = update_record(conn, table_map.get('receivers','receivers'), 'Receiver_ID', rid, updates)
                                if ok:
                                    refresh_after_crud('Receiver updated')
                                else:
                                    st.error(msg)
                                try:
                                    conn.close()
                                except Exception:
                                    pass
                            else:
                                st.error('No updates provided')

                else:  # Delete
                    recv_opts = []
                    recv_ids = []
                    if receivers is not None and 'Receiver_ID' in receivers.columns:
                        for _, r in receivers.iterrows():
                            recv_opts.append(str(r.get('Name')))
                            recv_ids.append(str(r.get('Receiver_ID')))
                    sel = st.selectbox('Select Receiver to delete', options=[''] + recv_opts)
                    submit = st.form_submit_button('Delete')
                    if submit:
                        if not sel:
                            st.error('Select a receiver')
                        else:
                            idx = recv_opts.index(sel)
                            rid = recv_ids[idx]
                            conn = get_db_connection(db_path=db_path)
                            ok, msg = delete_record(conn, table_map.get('receivers','receivers'), 'Receiver_ID', rid)
                            if ok:
                                refresh_after_crud('Receiver deleted')
                            else:
                                st.error(msg)
                            try:
                                conn.close()
                            except Exception:
                                pass


# Page router
if page == 'Overview':
    render_overview(df, filtered)
elif page == 'EDA':
    render_eda(filtered, providers, receivers)
elif page == 'Bivariate':
    render_bivariate(filtered, providers)
elif page == 'Multivariate':
    render_multivariate(filtered, providers)
elif page == 'Claims':
    render_claims(filtered)
elif page == 'Providers':
    render_providers(filtered, providers)
elif page == 'Query Outputs':
    render_queries(filtered, providers, receivers, claims, food)
elif page == 'Data':
    render_data(filtered)
elif page == 'Project':
        st.header('Project: Local Food Wastage Management System')
        # Render the provided project document content as HTML/Markdown
        project_html = r"""
        <div class='section'>
        <h2>Project: Local Food Wastage Management System</h2>
        <h3>1. Business Objective</h3>
        <p>To reduce food wastage by connecting food providers (restaurants, grocery stores, supermarkets, etc.) with receivers (NGOs, community centers, needy individuals) through a centralized platform.</p>
        <h4>Simple Explanation</h4>
        <p>Many restaurants throw away extra food every day. At the same time, many people struggle to get food. This system helps:</p>
        <ul>
            <li>Food Providers donate extra food</li>
            <li>NGOs/People claim food</li>
            <li>Food gets distributed instead of wasted</li>
            <li>Food wastage decreases</li>
            <li>Hunger issues are reduced</li>
        </ul>
        <h3>2. Business Problem</h3>
        <p><strong>Current Problems</strong></p>
        <ol>
            <li>Excess food is wasted.</li>
            <li>NGOs don't know where food is available.</li>
            <li>No centralized platform exists.</li>
            <li>Food distribution is inefficient.</li>
            <li>Providers and receivers cannot easily connect.</li>
            <li>No proper analysis of food donation trends.</li>
        </ol>
        <h4>Solution</h4>
        <p>Create a system where providers list food, receivers claim food, claims are tracked, data is stored in SQL, analysis is performed, and a Streamlit app provides an interface.</p>
        <h3>3. Datasets Used</h3>
        <p>You have 4 datasets: Providers, Receivers, Food Listings, Claims.</p>
        <h3>4. Null Value Analysis</h3>
        <p><strong>Providers</strong>: Contact missing, Address missing.</p>
        <p><strong>Receivers</strong>: Contact missing.</p>
        <p><strong>Food Listings</strong>: Expiry Date missing, Quantity missing.</p>
        <p><strong>Claims</strong>: Status missing, Timestamp missing.</p>
        <h3>5. Project Deliverables</h3>
        <p>EDA, charts, SQL queries, Streamlit Dashboard with filters and charts.</p>
        <h3>6. Business Insights You Should Find</h3>
        <ul>
            <li>Which city has the most food?</li>
            <li>Which meal gets wasted the most?</li>
            <li>Which provider contributes most?</li>
            <li>Which receiver claims most food?</li>
            <li>What percentage of claims are completed?</li>
        </ul>
        <h3>7. Business Recommendations</h3>
        <ul>
            <li>Cities with high food wastage should have more NGO partnerships.</li>
            <li>Providers contributing most food should receive recognition.</li>
            <li>Automated notifications should be sent before food expiry.</li>
            <li>Increase food collection efforts in high-demand cities.</li>
        </ul>
        </div>
        """
        st.markdown(project_html, unsafe_allow_html=True)
elif page == 'Actions':
    st.subheader('Actions — Interactive CRUD')
    st.markdown('Use the sections below to Add, Update, or Delete records. Each section contains separate forms for Donations, Claims, Providers, and Receivers.')
    # No URL-based auto-open behavior (compatibility fallback)
    st.markdown('Select an entity to manage')
    e1, e2 = st.columns(2)
    with e1:
        with st.expander('Claims', expanded=st.session_state.get('expand_Claims', False)):
            st.write('Manage Claims')
            if st.button('Add Claim'):
                open_modal('Claims', 'Add')
            if st.button('Update Claim'):
                open_modal('Claims', 'Update')
            if st.button('Delete Claim'):
                open_modal('Claims', 'Delete')
    with e2:
        with st.expander('Food Listings', expanded=st.session_state.get('expand_Food', False)):
            st.write('Manage Food Listings')
            if st.button('Add Food'):
                open_modal('Food', 'Add')
            if st.button('Update Food'):
                open_modal('Food', 'Update')
            if st.button('Delete Food'):
                open_modal('Food', 'Delete')

    e3, e4 = st.columns(2)
    with e3:
        with st.expander('Providers', expanded=st.session_state.get('expand_Providers', False)):
            st.write('Manage Providers')
            if st.button('Add Provider'):
                open_modal('Providers', 'Add')
            if st.button('Update Provider'):
                open_modal('Providers', 'Update')
            if st.button('Delete Provider'):
                open_modal('Providers', 'Delete')
    with e4:
        with st.expander('Receivers', expanded=st.session_state.get('expand_Receivers', False)):
            st.write('Manage Receivers')
            if st.button('Add Receiver'):
                open_modal('Receivers', 'Add')
            if st.button('Update Receiver'):
                open_modal('Receivers', 'Update')
            if st.button('Delete Receiver'):
                open_modal('Receivers', 'Delete')

    # Render modal if requested
    if 'modal_open' not in st.session_state:
        st.session_state['modal_open'] = False
        st.session_state['modal_entity'] = None
        st.session_state['modal_action'] = None
    render_action_modal(providers, receivers, food, claims)
