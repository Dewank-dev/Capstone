import pandas as pd
import mysql.connector
from mysql.connector import Error


def load_data(file_like):
    df = pd.read_csv(file_like)
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    # Parse dates if column exists
    for col in ['PickupDate', 'pickup_date', 'Date', 'date']:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass
    # Ensure Quantity is numeric
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    return df


def load_providers(file_like):
    df = pd.read_csv(file_like)
    df.columns = [c.strip() for c in df.columns]
    # Standardize provider id and name
    for col in ['Provider_ID', 'ProviderId', 'Provider Id']:
        if col in df.columns:
            df = df.rename(columns={col: 'Provider_ID'})
            break
    for col in ['Name', 'ProviderName']:
        if col in df.columns:
            df = df.rename(columns={col: 'ProviderName'})
            break
    # Contact
    if 'Contact' not in df.columns and 'Phone' in df.columns:
        df = df.rename(columns={'Phone': 'Contact'})
    return df


def get_db_connection(host='localhost', port=3306, user='root', password='', database=None):
    """Return a mysql.connector connection. Caller should handle closing.

    Defaults assume a local MySQL on port 3306. Set `database` to select a schema.
    """
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        return conn
    except Error:
        return None


def _read_table(conn, table_name):
    try:
        sql = f"SELECT * FROM `{table_name}`"
        return pd.read_sql(sql, conn)
    except Exception:
        return pd.DataFrame()


def load_providers_from_df(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    for col in ['Provider_ID', 'ProviderId', 'Provider Id']:
        if col in df.columns:
            df = df.rename(columns={col: 'Provider_ID'})
            break
    for col in ['Name', 'ProviderName']:
        if col in df.columns:
            df = df.rename(columns={col: 'ProviderName'})
            break
    if 'Contact' not in df.columns and 'Phone' in df.columns:
        df = df.rename(columns={'Phone': 'Contact'})
    return df


def load_receivers_from_df(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    for col in ['Receiver_ID', 'ReceiverId']:
        if col in df.columns:
            df = df.rename(columns={col: 'Receiver_ID'})
            break
    if 'Contact' not in df.columns and 'Phone' in df.columns:
        df = df.rename(columns={'Phone': 'Contact'})
    return df


def load_food_listings_from_df(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    if 'Food_ID' not in df.columns and 'FoodId' in df.columns:
        df = df.rename(columns={'FoodId': 'Food_ID'})
    if 'Expiry_Date' in df.columns:
        try:
            df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date'], errors='coerce')
        except Exception:
            pass
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    if 'Location' in df.columns and 'City' not in df.columns:
        df = df.rename(columns={'Location': 'City'})
    return df


def load_claims_from_df(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    if 'Timestamp' in df.columns:
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        except Exception:
            pass
    if 'Status' not in df.columns and 'ClaimStatus' in df.columns:
        df = df.rename(columns={'ClaimStatus': 'Status'})
    return df


def load_all_from_db(conn, table_map=None):
    """Load providers, receivers, food_listings, claims from DB connection.

    `table_map` is an optional dict to map logical names to actual table names, e.g.
    {'providers': 'providers', 'receivers': 'receivers', 'food': 'food_listings', 'claims': 'claims'}
    Returns tuple (providers, receivers, food, claims)
    """
    if table_map is None:
        table_map = {'providers': 'providers', 'receivers': 'receivers', 'food': 'food_listings', 'claims': 'claims'}
    prov = _read_table(conn, table_map.get('providers', 'providers'))
    recv = _read_table(conn, table_map.get('receivers', 'receivers'))
    food = _read_table(conn, table_map.get('food', 'food_listings'))
    claims = _read_table(conn, table_map.get('claims', 'claims'))
    # Apply dataframe-based loaders to normalize columns
    prov = load_providers_from_df(prov) if not prov.empty else None
    recv = load_receivers_from_df(recv) if not recv.empty else None
    food = load_food_listings_from_df(food) if not food.empty else None
    claims = load_claims_from_df(claims) if not claims.empty else None
    return prov, recv, food, claims


def write_df_to_table(conn, df, table_name, truncate=True):
    """Write a pandas DataFrame to an existing MySQL table using mysql.connector.

    This function will `TRUNCATE` the table first if `truncate=True`.
    It expects the table schema to already exist and the DataFrame column names
    to match the table column names.
    Returns True on success, False on failure.
    """
    if df is None or df.empty:
        return False, 'empty dataframe'
    cursor = conn.cursor()
    try:
        # Ensure table exists; if not, attempt to create it from DataFrame
        try:
            cursor.execute(f"SELECT 1 FROM `{table_name}` LIMIT 1")
            try:
                cursor.fetchall()
            except Exception:
                pass
        except Exception:
            # create table
            if not _create_table_from_df(conn, table_name, df):
                return False, 'failed to create table'
            try:
                cursor.close()
            except Exception:
                pass
            cursor = conn.cursor()
        if truncate:
            cursor.execute(f"TRUNCATE TABLE `{table_name}`")
        cols = list(df.columns)
        col_names = ",".join([f"`{c}`" for c in cols])
        placeholders = ",".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"
        values = []
        for row in df[cols].itertuples(index=False, name=None):
            # convert numpy types and NaN
            cleaned = tuple(None if (pd.isna(x)) else x for x in row)
            values.append(cleaned)
        if values:
            cursor.executemany(sql, values)
        conn.commit()
        return True, ''
    except Exception as e:
        err = str(e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False, err
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def insert_record(conn, table_name, record):
    """Insert a single record (dict) into `table_name`. Returns (True, '') or (False, error)."""
    if not record:
        return False, 'empty record'
    cols = list(record.keys())
    col_names = ",".join([f"`{c}`" for c in cols])
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})"
    vals = [record[c] for c in cols]
    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(vals))
        conn.commit()
        return True, ''
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def update_record(conn, table_name, pk_col, pk_value, updates):
    """Update a record by primary key column. `updates` is a dict of column->value."""
    if not updates:
        return False, 'no updates'
    set_clause = ",".join([f"`{k}`=%s" for k in updates.keys()])
    sql = f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_col}`=%s"
    vals = list(updates.values()) + [pk_value]
    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(vals))
        conn.commit()
        return True, ''
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def delete_record(conn, table_name, pk_col, pk_value):
    """Delete a record by primary key column."""
    sql = f"DELETE FROM `{table_name}` WHERE `{pk_col}`=%s"
    cur = conn.cursor()
    try:
        cur.execute(sql, (pk_value,))
        conn.commit()
        return True, ''
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _sql_type_for_series(s):
    if pd.api.types.is_integer_dtype(s):
        return 'INT'
    if pd.api.types.is_float_dtype(s):
        return 'DOUBLE'
    if pd.api.types.is_bool_dtype(s):
        return 'BOOLEAN'
    if pd.api.types.is_datetime64_any_dtype(s):
        return 'DATETIME'
    # default to TEXT for strings/mixed
    return 'TEXT'


def _create_table_from_df(conn, table_name, df):
    """Create a simple table schema in MySQL based on a pandas DataFrame.

    Column types are guessed conservatively. Returns True on success.
    """
    cols = []
    for col in df.columns:
        safe_col = str(col).strip()
        try:
            col_type = _sql_type_for_series(df[col])
        except Exception:
            col_type = 'TEXT'
        cols.append(f"`{safe_col}` {col_type}")
    # pick primary key if a column ends with _ID or Id
    pk = None
    for col in df.columns:
        if str(col).lower().endswith('_id') or str(col).lower().endswith('id'):
            pk = str(col)
            break
    pk_sql = f", PRIMARY KEY (`{pk}`)" if pk is not None else ''
    create_sql = f"CREATE TABLE `{table_name}` ({', '.join(cols)}{pk_sql}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    cur = conn.cursor()
    try:
        cur.execute(create_sql)
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass


def load_receivers(file_like):
    df = pd.read_csv(file_like)
    df.columns = [c.strip() for c in df.columns]
    for col in ['Receiver_ID', 'ReceiverId']:
        if col in df.columns:
            df = df.rename(columns={col: 'Receiver_ID'})
            break
    if 'Contact' not in df.columns and 'Phone' in df.columns:
        df = df.rename(columns={'Phone': 'Contact'})
    return df


def load_food_listings(file_like):
    df = pd.read_csv(file_like)
    df.columns = [c.strip() for c in df.columns]
    # Normalize common columns
    if 'Food_ID' not in df.columns and 'FoodId' in df.columns:
        df = df.rename(columns={'FoodId': 'Food_ID'})
    if 'Expiry_Date' in df.columns:
        try:
            df['Expiry_Date'] = pd.to_datetime(df['Expiry_Date'], errors='coerce')
        except Exception:
            pass
    if 'Quantity' in df.columns:
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    # Location / City
    if 'Location' in df.columns and 'City' not in df.columns:
        df = df.rename(columns={'Location': 'City'})
    return df


def load_claims(file_like):
    df = pd.read_csv(file_like)
    df.columns = [c.strip() for c in df.columns]
    if 'Timestamp' in df.columns:
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        except Exception:
            pass
    if 'Status' not in df.columns and 'ClaimStatus' in df.columns:
        df = df.rename(columns={'ClaimStatus': 'Status'})
    return df


def merge_datasets(providers=None, receivers=None, food=None, claims=None):
    # Merge providers and food listings on Provider_ID
    if food is None:
        return None
    df = food.copy()
    if providers is not None and 'Provider_ID' in df.columns and 'Provider_ID' in providers.columns:
        # prefer provider name and contact
        df = df.merge(providers[['Provider_ID', 'ProviderName', 'Contact', 'City']], on='Provider_ID', how='left')
        if 'ProviderName' in df.columns:
            df = df.rename(columns={'ProviderName': 'Provider'})
        if 'Contact' in df.columns:
            df = df.rename(columns={'Contact': 'ProviderContact'})
    # Merge claims
    if claims is not None and 'Food_ID' in df.columns and 'Food_ID' in claims.columns:
        # bring claim info; there can be multiple claims per food - we will left-join claims and keep latest status per food
        latest_claims = claims.sort_values('Timestamp').groupby('Food_ID').last().reset_index()
        df = df.merge(latest_claims[['Food_ID', 'Status', 'Receiver_ID', 'Timestamp']], on='Food_ID', how='left')
        df = df.rename(columns={'Status': 'ClaimStatus', 'Timestamp': 'ClaimTimestamp'})
    # Enrich receivers
    if receivers is not None and 'Receiver_ID' in df.columns:
        df = df.merge(receivers[['Receiver_ID', 'Name']], left_on='Receiver_ID', right_on='Receiver_ID', how='left')
        df = df.rename(columns={'Name': 'ReceiverName'})
    # Consolidate City columns if merge introduced duplicates (City_x, City_y)
    if 'City' not in df.columns:
        if 'City_x' in df.columns:
            df['City'] = df['City_x']
        elif 'City_y' in df.columns:
            df['City'] = df['City_y']
        elif 'Location' in df.columns:
            df['City'] = df['Location']
    # If both City_x and City_y exist, prefer non-null from City_x then City_y
    if 'City_x' in df.columns and 'City_y' in df.columns:
        df['City'] = df['City_x'].fillna(df['City_y'])
        # drop extra columns
        df = df.drop(columns=[c for c in ['City_x', 'City_y'] if c in df.columns])
    return df


def aggregate_by_city(df):
    if df is None or 'City' not in df.columns:
        return pd.DataFrame()
    return df.groupby('City')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)


def provider_contributions(df):
    if df is None or 'Provider' not in df.columns:
        return pd.DataFrame()
    return df.groupby('Provider')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)


def claims_completion_rate(df):
    if df is None or 'ClaimStatus' not in df.columns:
        return {'completed': 0, 'total': 0, 'pct_completed': 0}
    total = len(df)
    completed = df['ClaimStatus'].astype(str).str.lower().isin(['completed', 'complete', 'done', 'claimed']).sum()
    pct = 100.0 * completed / max(1, total)
    return {'completed': int(completed), 'total': int(total), 'pct_completed': pct}



def get_filters(df):
    filters = {}
    # helper to find first existing column from variants
    def find_col(variants):
        for v in variants:
            if v in df.columns:
                return v
        return None

    city_col = find_col(['City', 'city', 'Location', 'location'])
    if city_col:
        filters['City'] = {'type': 'multi', 'options': sorted(df[city_col].dropna().unique()), 'col': city_col}

    provider_col = find_col(['Provider', 'ProviderName', 'Name'])
    if provider_col:
        filters['Provider'] = {'type': 'multi', 'options': sorted(df[provider_col].dropna().unique()), 'col': provider_col}

    meal_col = find_col(['MealType', 'Meal_Type', 'Meal Type'])
    if meal_col:
        filters['Meal Type'] = {'type': 'multi', 'options': sorted(df[meal_col].dropna().unique()), 'col': meal_col}

    food_col = find_col(['FoodType', 'Food_Type', 'Food Type'])
    if food_col:
        filters['Food Type'] = {'type': 'multi', 'options': sorted(df[food_col].dropna().unique()), 'col': food_col}

    # Date filter (expiry or claim timestamp)
    date_col = None
    for col in ['Expiry_Date', 'ExpiryDate', 'PickupDate', 'pickup_date', 'Timestamp', 'ClaimTimestamp', 'date', 'Date']:
        if col in df.columns and pd.api.types.is_datetime64_any_dtype(df[col]):
            date_col = col
            break
    if date_col:
        filters['Date Range'] = {'type': 'date', 'min': df[date_col].min(), 'max': df[date_col].max(), 'col': date_col}
    return filters


def filter_data(df, filters_meta, selected_filters):
    out = df.copy()
    for label, opts in filters_meta.items():
        if label not in selected_filters:
            continue
        val = selected_filters[label]
        col = opts.get('col', label)
        if col not in out.columns:
            continue
        if opts['type'] == 'multi':
            if isinstance(val, list) and len(val) > 0:
                out = out[out[col].isin(val)]
        elif opts['type'] == 'date':
            try:
                start, end = val
                out = out[(out[col].dt.date >= start) & (out[col].dt.date <= end)]
            except Exception:
                pass
    return out


def compute_kpis(df):
    total = int(len(df))
    total_quantity = float(df['Quantity'].sum()) if 'Quantity' in df.columns else 0.0
    pct_completed = 0.0
    if 'ClaimStatus' in df.columns:
        completed = df['ClaimStatus'].astype(str).str.lower().isin(['completed', 'complete', 'done', 'claimed'])
        pct_completed = 100.0 * completed.sum() / max(1, total)
    top_provider = None
    if 'Provider' in df.columns and 'Quantity' in df.columns:
        grp = df.groupby('Provider')['Quantity'].sum().sort_values(ascending=False)
        if len(grp) > 0:
            top_provider = grp.index[0]
    return {
        'total': total,
        'total_quantity': total_quantity,
        'pct_completed': pct_completed,
        'top_provider': top_provider or 'N/A'
    }
