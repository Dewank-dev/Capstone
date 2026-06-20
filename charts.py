import plotly.express as px
from plotly.colors import qualitative


def _apply_base_layout(fig, height=None):
    fig.update_layout(
        template='plotly_white',
        margin=dict(l=40, r=20, t=60, b=60),
        title=dict(font=dict(size=18)),
        legend=dict(font=dict(size=12)),
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(title_font=dict(size=14), tickfont=dict(size=11))
    fig.update_yaxes(title_font=dict(size=14), tickfont=dict(size=11))
    return fig


def plot_bar(df, groupby, value_col=None):
    if groupby not in df.columns:
        return px.bar(title=f"No column {groupby}")

    if value_col and value_col in df.columns:
        agg = df.groupby(groupby)[value_col].sum().reset_index()
        agg = agg.sort_values(value_col, ascending=True)
        many = len(agg) > 12
        height = 400 if not many else max(400, len(agg) * 28)
        if many:
            fig = px.bar(agg, x=value_col, y=groupby, orientation='h', title=f"{value_col} by {groupby}", color=value_col, color_continuous_scale='Blues')
            fig.update_traces(texttemplate='%{x:.2s}', textposition='auto')
        else:
            fig = px.bar(agg, x=groupby, y=value_col, title=f"{value_col} by {groupby}", color=groupby, color_discrete_sequence=qualitative.Plotly)
            fig.update_traces(texttemplate='%{y:.2s}', textposition='auto')
    else:
        agg = df[groupby].value_counts().reset_index()
        agg.columns = [groupby, 'count']
        agg = agg.sort_values('count', ascending=True)
        many = len(agg) > 12
        height = 400 if not many else max(400, len(agg) * 28)
        if many:
            fig = px.bar(agg, x='count', y=groupby, orientation='h', title=f"Count by {groupby}", color='count', color_continuous_scale='Aggrnyl')
            fig.update_traces(texttemplate='%{x}', textposition='auto')
        else:
            fig = px.bar(agg, x=groupby, y='count', title=f"Count by {groupby}", color=groupby, color_discrete_sequence=qualitative.Plotly)
            fig.update_traces(texttemplate='%{y}', textposition='auto')

    fig.update_traces(marker_line_color='rgba(0,0,0,0.06)', marker_line_width=0.5, opacity=0.95)
    fig = _apply_base_layout(fig, height=height)
    # rotate ticks for vertical bars when category names are long
    if not (value_col and len(df[groupby].unique()) > 12):
        fig.update_xaxes(tickangle=-45)
    return fig


def plot_histogram(df, col):
    if col not in df.columns:
        return px.histogram(title=f"No column {col}")
    # choose bins adaptively
    unique_vals = df[col].dropna().unique()
    nbins = 40 if len(unique_vals) > 50 else min(40, max(10, int(len(unique_vals) / 2)))
    fig = px.histogram(df, x=col, nbins=nbins, title=f"Distribution of {col}")
    fig.update_traces(marker=dict(line=dict(width=0.5, color='white')), opacity=0.9)
    fig = _apply_base_layout(fig, height=420)
    return fig


def plot_pie(df, names_col, values_col=None, title=None):
    if names_col not in df.columns:
        return px.pie(names=[], values=[], title=f"No column {names_col}")
    if values_col and values_col in df.columns:
        agg = df.groupby(names_col)[values_col].sum().reset_index()
        agg = agg.sort_values(values_col, ascending=False)
        fig = px.pie(agg, names=names_col, values=values_col, title=title or f"{values_col} by {names_col}", hole=0.25)
    else:
        agg = df[names_col].value_counts().reset_index()
        agg.columns = [names_col, 'count']
        agg = agg.sort_values('count', ascending=False)
        fig = px.pie(agg, names=names_col, values='count', title=title or f"Count by {names_col}", hole=0.25)

    fig.update_traces(textposition='inside', textinfo='percent+label', pull=[0.02 if i == 0 else 0 for i in range(len(fig.data[0]['labels']))])
    fig = _apply_base_layout(fig, height=420)
    return fig
