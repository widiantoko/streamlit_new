import pandas as pd
import numpy as np
import streamlit as st
import tomllib
from sqlalchemy import create_engine
from streamlit_option_menu import option_menu
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Range1d, LabelSet
import math
from datetime import datetime, timedelta, timezone
from streamlit_bokeh import streamlit_bokeh
from bokeh.embed import components
import plotly.graph_objects as go
import geopandas as gpd
import plotly.express as px
import os
import json
from bokeh.models import Title

st.set_page_config(page_title="CitoXpress", layout='wide')
#st.set_page_config(page_title="Kiriman Ke Cabang dan Agen", layout='wide')

# ==================== FUNGSI DATABASE ====================
def fetch_data(db_key="mysql01"):
    """Fungsi untuk mengambil data dari database"""
    try:
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)[db_key]
        
        url = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 3306)}/{config['database']}"
        engine = create_engine(url)
        
        query = """
            SELECT konid, DATE_FORMAT(tanggal,'%M_%Y') as bln_thn, 
                   d.nmpelanggan, kdproduk, kdmani, jenis, left(a.tujuan,2) as kdprop,
                   6 * (DATEDIFF(CURRENT_DATE, tanggal) DIV 7) + MID('0123455501234445012333450122234501112345000123450', 
                   7 * WEEKDAY(tanggal) + WEEKDAY(CURRENT_DATE) + 1, 1) as diff2
            FROM tkonos a 
            LEFT JOIN mpelanggan d ON LEFT(a.kdpelanggan,8) = d.kdpelanggan 
            WHERE tanggal >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 3 MONTH), '%Y-%m-01') 
              AND a.pod=' ' and a.kdpelanggan like 'CBH%'
              and kdproduk in ('N','U','T','D') 
              and kdkirim in ('C', 'D') 
              and a.kdpelanggan not like 'CBH17002%' 
              and jenis<>'I' and awbno<>' '
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            return pd.DataFrame(columns=['konid', 'bln_thn', 'nmpelanggan', 'kdproduk', 'kdmani', 'jenis', 'kdprop', 'diff2'])
        
        # Membersihkan nama pelanggan
        if 'nmpelanggan' in df.columns:
            df['pelanggan'] = df['nmpelanggan'].str.replace(",", " ").fillna("UNKNOWN").str.split().str[:2].str.join(" ")
        
        return df
        
    except Exception as e:
        print(f"ERROR DATABASE: {e}")
        return pd.DataFrame()

 # Ambil data dari database



#path='/Users/dodiwidiantoko/Documents/shiny_python/peta'
# Harusnya menggunakan path relatif
path = os.path.join(os.path.dirname(__file__), 'peta')  # ✅ BENAR

provinsi_indonesia = ['11_aceh.geojson', '12_sumut.geojson','13_sumbar.geojson',
                      '14_riau.geojson','15_jambi.geojson','16_sumsel.geojson','18_lampung.geojson',
                      '19_babel.geojson','17_bengkulu.geojson','21_kepri.geojson','31_dki.geojson',
                      '32_jabar.geojson','33_jateng.geojson','35_jatim.geojson','36_banten.geojson',
                      '61_kalbar.geojson','62_kalteng.geojson','64_kaltim.geojson','63_kalsel.geojson','65_kaltara.geojson',
                      '51_bali.geojson','52_ntb.geojson','53_ntt.geojson','71_sulut.geojson','72_sulteng.geojson',
                        '73_sulsel.geojson','74_sultra.geojson','75_gorontalo.geojson','76_sulbar.geojson',
                        '81_maluku.geojson','82_malut.geojson','91_papua.geojson','94_papua_tengah.geojson',
                        '92_papua_barat.geojson','93_papua_selatan.geojson','95_papua_pegunungan.geojson',
                        '96_papua_barat_daya.geojson'
                        

                      ]



# Baca dan gabungkan semua file
gdf_list = []



for file in provinsi_indonesia:
    try:
        file_path = os.path.join(path, file)
        gdf = gpd.read_file(file_path)
        nama = gdf['name'].iloc[0]
        
            
        
        # Tambahkan kolom
        gdf['provinsi'] = nama
        #gdf['penduduk'] = data_penduduk.get(nama, 0)

        nama_prov = gdf['provinsi'].iloc[0]
        #penduduk = gdf['penduduk'].iloc[0]
        
        gdf_list.append(gdf)
        #st.success(f"✅ {nama} berhasil dimuat")
        
    except Exception as e:
        st.error(f"❌ Gagal memuat {file}: {e}")








# ==================== PAGE FUNCTIONS ====================



 


def page_1():
    """Halaman utama untuk Kiriman Belum Ada Status"""
    
    row1_col1, row1_col2 = st.columns(2, gap="medium")
    row2_col1, row2_col2 = st.columns(2, gap="medium")
    row3_col1 = st.columns(1)[0] 

    df = fetch_data()

    #st.title("Kinerja Kiriman Belum Ada Status")

    #st.dataframe(df.head(10))
    
       
    
    with row1_col1:
     
                
        st.markdown("""<h6 style='font-size: 20px; color: #1565C0; 
                    display: flex; align-items: center; margin-top: 10px; margin-bottom: 0px;             
                    '>Pilih Bulan:</h6>""", 
           unsafe_allow_html=True, text_alignment="left")  
        # CSS untuk meratakan radio button di tengah

        
        bulan_urut = sorted(
        df['bln_thn'].unique(),key=lambda x: pd.to_datetime(x, format="%B_%Y"))

        # Radio button Anda
        pilihan = st.radio("Pilih Bulan:", options=bulan_urut, horizontal=True, label_visibility="collapsed")
     



        datafr= df[df['bln_thn'] == pilihan]    
        dok_qty= df[(df['bln_thn'] == pilihan) & (df['jenis'] == 'C')]
        pkt_qty= df[(df['bln_thn'] == pilihan) & (df['jenis'] == 'D')]
        
        #data_hasil= df.groupby(['kdprop']).apply(lambda x: x[x['bln_thn'] == pilihan]['konid'].count())
        data_hasil = df.groupby(['kdprop'], group_keys=False).apply(lambda x: x[x['bln_thn'] == pilihan]['konid'].count()
)



        data_hasil = data_hasil.rename('total_konid').reset_index()
        max_konid = data_hasil['total_konid'].max()

        # Rename the 'Value' column to 'Count'
        #data_hasil = data_hasil.rename(columns={'Value': 'Count'})
        #print (df.info())
        


        #data_hasil.columns = ['kdprop', 'jumlah_kiriman']
    
    if df.empty:
        st.warning("Tidak ada data untuk ditampilkan.")
        return st.container()

    with row1_col2:

         
        all= f"{len(datafr)} Kiriman"
        dok_pkt= f""" {len(dok_qty)} Dokumen + {len(pkt_qty)} Paket """


        st.markdown(f"""
                    <h4 style='font-size: 30px; margin-top: 25px; color: #1565C0;'>{all} : {dok_pkt} </h4> """, 
            unsafe_allow_html=True, text_alignment="left")   


    st.divider()

    with row2_col1:

        # Data untuk chart
        hasil2a = datafr.groupby("kdmani").size().reset_index(name='no_status').sort_values("no_status", ascending=False).head(12)
        hasil2c = datafr.groupby(["pelanggan", "kdproduk"]).size().reset_index(name='rekap').sort_values("rekap", ascending=False)
        

        # Pivot table untuk produk
        pivot_2c = hasil2c.pivot_table(
            values='rekap', 
            index=['pelanggan'], 
            columns=['kdproduk'], 
            aggfunc='sum'
        ).fillna(0)

       
        
        # Rename kolom produk
        rename_map = {'N': 'Normal', 'U': 'Urgent', 'T': 'Top Urgent', 
                      'D': 'Darat', 'C': 'Trucking', 'P': 'Premium'}
        pivot_2c.rename(columns=rename_map, inplace=True)
        
        # Hitung total
        pivot_2c['sum'] = pivot_2c.sum(axis=1)
        final = pivot_2c.sort_values("sum", ascending=False).head(11)

        top=(len(final)-1)
        
        # Ambil kolom produk
        produk_cols = [col for col in final.columns if col not in ['pelanggan', 'sum']]
        
        # Hitung upper limit
        upper_lmt = math.ceil(final['sum'].max() * 1.1 / 10) * 10
        #upper_lmt=round(final["sum"].nlargest(1)*1.1, -1)
        
        # Warna untuk setiap produk
        wr = {
            'Normal': '#64B5F6',
            'Urgent': '#1565C0',
            'Top Urgent': '#FF8A80',
            'Trucking': '#1DE9B6',
            'Darat': '#FDD835',
            'Premium': '#F48FB1'
        }
        
        # Buat figure Bokeh
        ph = figure(
            #y_range=final.index.tolist()[::-1],
            y_range=final.index.tolist()[:-1],
            height=275,
            width=300,
            tools="hover",
            tooltips="$name : @$name",
            toolbar_location=None,
            margin=(10, 0, 0, 0),
            
        )
        
        # Horizontal bar stack
        ph.hbar_stack(
            produk_cols,
            y='pelanggan',
            height=0.7,
            color=[wr.get(col, '#gray') for col in produk_cols],
            source=ColumnDataSource(final.reset_index()),
            legend_label=produk_cols
        )
        
        # Tambahkan title sebagai objek terpisah
        title = Title(
        text= f"Kiriman Belum Ada Status untuk {top} Pelanggan Teratas",
        align="center",
        text_font_size="14pt",
        text_font_style="bold",
        text_color="#3D3D3F",
        background_fill_color="#f0f0f0",
        background_fill_alpha=0.15
)

        ph.title = title  # Set title object




        # Styling
        ph.ygrid.grid_line_color = None
        ph.x_range = Range1d(0, upper_lmt)
        ph.legend.orientation = "horizontal"
        ph.add_layout(ph.legend[0], 'below')
        ph.outline_line_color = None
        ph.legend.location = "bottom_center"
        
        # Legend styling
        ph.legend.margin = 30
        ph.legend.padding = 15
        ph.legend.spacing = 10
        ph.legend.border_line_width = 1
        ph.legend.border_line_color = "lightgray"
        ph.legend.border_line_alpha = 0.5

        streamlit_bokeh(ph, use_container_width=True)



    with row2_col2:

        
        # Clustering menggunakan Numpy Select
        conditions = [
        (datafr['diff2'] <= 3),
        (datafr['diff2'] > 3) & (datafr['diff2'] <= 7),
        (datafr['diff2'] > 7) & (datafr['diff2'] <= 14),
        (datafr['diff2'] > 14) & (datafr['diff2'] <= 30),
        (datafr['diff2'] > 30) & (datafr['diff2'] <= 60),
        (datafr['diff2'] > 60)
    ]
        choices = ['a. 0 - 3 hari', 'b. 4 - 7 hari', 'c. 8 - 14 hari', 
               'd. 15 - 30 hari', 'e. 31 - 60 hari', 'f. 61 hari - dst']
        #datafr['cluster_LT'] = np.select(conditions, choices, default='f. 61 hari - dst')
        # Pastikan Anda membuat copy terpisah
        datafr = datafr.copy()  # Tambahkan ini sebelum memodifikasi
        datafr['cluster_LT'] = np.select(conditions, choices, default='f. 61 hari - dst')



        #st.dataframe(datafr.head(20))

        # Chart untuk kdmani
        if not hasil2a.empty:
            # Data untuk chart kdmani
            hasil2b = datafr.groupby(["kdmani", "bln_thn", "cluster_LT"]).size().reset_index(name='no_status')
            
            # Filter berdasarkan kdmani teratas
            listkdmani = hasil2a["kdmani"].tolist()
            hasil2b_filtered = hasil2b[hasil2b['kdmani'].isin(listkdmani)]
            
            # Pivot table
            pivot_LT = hasil2b_filtered.pivot_table(
                values='no_status',
                index=['kdmani'],
                columns=['cluster_LT'],
                #aggfunc=np.sum
                aggfunc='sum'
            ).fillna(0)
            
            # Merge dengan hasil2a
            join_inner = pd.merge(hasil2a, pivot_LT, how="left", on=['kdmani'])
            
            # Urutan cluster
            clt = ['a. 0 - 3 hari', 'b. 4 - 7 hari', 'c. 8 - 14 hari',
                   'd. 15 - 30 hari', 'e. 31 - 60 hari', 'f. 61 hari - dst']
            
            # Ambil cluster yang ada di data
            available_clusters = [c for c in clt if c in join_inner.columns]
            
            # Warna untuk setiap cluster
            warna2 = {
                'a. 0 - 3 hari': '#9CCC65',
                'b. 4 - 7 hari': '#E6EE9C',
                'c. 8 - 14 hari': '#FFF59D',
                'd. 15 - 30 hari': '#FFD54F',
                'e. 31 - 60 hari': '#FFB74D',
                'f. 61 hari - dst': '#FF5722'
            }
            
            # Hitung y_atas
            y_atas = math.ceil(join_inner['no_status'].max() * 1.15 / 10) * 10
            
            # Buat figure
            pv = figure(
                x_range=join_inner['kdmani'].tolist(),
                height=275,
                width=300,
                toolbar_location=None,
                margin=(15, 0, 0, 0),  # (top, right, bottom, left) dalam pixel
                tools="hover",
                tooltips="$name @kdmani: @$name"
            )
            
            # Vertical bar stack
            pv.vbar_stack(
                available_clusters,
                x='kdmani',
                width=0.8,
                color=[warna2.get(c, '#808080') for c in available_clusters],
                source=ColumnDataSource(join_inner),
                legend_label=available_clusters
            )
            
            # Styling
            pv.y_range = Range1d(0, y_atas)
            pv.xgrid.grid_line_color = None
            pv.legend.location = "top_left"
            pv.legend.orientation = "horizontal"
            pv.add_layout(pv.legend[0], 'below')
            pv.outline_line_color = None

            # Tambahkan title sebagai objek terpisah
            title = Title(
            text= f"Kiriman Ada Status untuk {top} Cabang/Agen Teratas",
            align="center",
            text_font_size="16pt",
            text_font_style="bold",
            text_color="#0E0E0F",
            background_fill_color="#f0f0f0",
            background_fill_alpha=0.15
)

            pv.title = title  # Set title object


            # Margin di sekitar legend (jarak ke tepi plot)
            pv.legend.margin = 30

        # Padding di dalam legend (jarak teks ke border)
            pv.legend.padding = 15

        # Spacing antar item legend
            pv.legend.spacing = 10

        # Border legend
            pv.legend.border_line_width = 1
            pv.legend.border_line_color = "lightgray"
            pv.legend.border_line_alpha = 0.5   
            
            # Tampilkan chart

            streamlit_bokeh(pv, 
                            use_container_width=True,  # Responsif
                            theme="streamlit",          # Mengikuti tema Streamlit
                            key="plot_1"               )# UNIK untuk setiap plot)


    with row3_col1:


        gdf_list = []

        for file in provinsi_indonesia:
            try:
                file_path = os.path.join(path, file)
                gdf = gpd.read_file(file_path)
                kdprop = gdf['code'].iloc[0]
        
            
        
                # Tambahkan kolom
                gdf['kdprop'] = kdprop
                gdf ['total_konid'] = gdf['code'].map(data_hasil.set_index('kdprop')['total_konid']).fillna(0)

                \
                gdf_list.append(gdf)
     
        
            except Exception as e:
                st.error(f"❌ Gagal memuat {file}: {e}")

        #gdf_list
        # Gabungkan semua GeoDataFrame
            gdf_gabungan = pd.concat(gdf_list, ignore_index=True)
        #st.dataframe(gdf_gabungan[['provinsi', 'penduduk']].drop_duplicates())
    
    
    
        # Konversi ke GeoJSON
        geojson = json.loads(gdf_gabungan.to_json())




        #st.dataframe(gdf_gabungan.head(38)) 
       

        
    
        # Buat figure
        fig = px.choropleth(
            gdf_gabungan,
            geojson=geojson,
            locations=gdf_gabungan['name'],  # Kolom yang berisi nama provinsi
            featureidkey="properties.name",
            color='total_konid',
            range_color=(0, max_konid),
            color_continuous_scale='Blues',
            hover_name='name',
            hover_data={'name':False, 'total_konid': ':,.0f'},  # Format hover
            title='Sebaran Kiriman Belum Ada Status Berdasarkan Propinsi',
        #hovertemplate='penduduk: %{z:,.0f}<extra></extra>'
        #hover_data=hover_text,
        #projection='mercator'
    )

        
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=700, width=2000, margin=dict(l=0, r=0, t=0, b=0) )# Margin minimal
        fig.update_layout(dragmode=False, title_x=0.24, title_y=0.95, title_font_size=20, title_font_color="#1565C0", 
                          title_font_family="Arial",
        hoverlabel=dict(
        bgcolor="white",
        font_size=14,
        font_family="Arial"
    )
)

        fig.update_traces(
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>" +
        "<b>%{customdata[1]:,.0f} </b><br><br>" +
                "<extra></extra>"
    )
)

    
        st.plotly_chart(fig, width='content')














        #st.markdown("---")
 



def page_2():
    return st.container()

def page_3():
    return st.container()

def page_4():
    return st.container()






selected2 = option_menu("Dashboard Operasional CitoXpress", ["Kiriman Belum Ada Status", "Kiriman Intracity Jakarta", "Volume Kiriman", "Review Kinerja"],
    icons=['bi bi-envelope-exclamation', 'bi bi-exclamation-circle', 'bi bi-boxes', 'gear'], 
    menu_icon="cast", default_index=0, orientation="horizontal")

if selected2=="Kiriman Belum Ada Status":
    page_1()
elif selected2=="Kiriman Intracity Jakarta":
    page_2()
elif selected2=="Volume Kiriman":
    page_3()
elif selected2=="Review Kinerja":
    page_4()