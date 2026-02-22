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




def fetch_data2(db_key="mysql01"):
    """Fungsi untuk mengambil data volume kiriman"""
    try:
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)[db_key]
        
        url = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 3306)}/{config['database']}"
        engine = create_engine(url)
        
        query = """
            SELECT 
                YEAR(tanggal) as tahun, 
                MONTHNAME(tanggal) as bulan,  
                DATE_FORMAT(tanggal,'%b_%y') as bln_thn,
                COUNT(konid) as qty_pcs, 
                ROUND(SUM(berat), 0) as berat_kg 
            FROM tkonos 
            WHERE tanggal >= '2025-10-01' 
                AND tanggal <= NOW() 
                AND kdpelanggan NOT LIKE 'CBH17002%' 
                AND (kdpelanggan LIKE 'CBH%' 
                    OR kdpelanggan LIKE 'CTG%' 
                    OR kdpelanggan LIKE 'CBO%' 
                    OR kdpelanggan LIKE 'CBK%') 
                AND kdproduk IN ('N', 'U', 'T', 'D', 'P')
            GROUP BY YEAR(tanggal), MONTH(tanggal)
            ORDER BY YEAR(tanggal) ASC, MONTH(tanggal) ASC
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        return df
        
    except Exception as e:
        print(f"ERROR DATABASE (fetch_volume_data): {e}")
        return pd.DataFrame()

def fetch_data3(db_key="mysql02"):
    """Fungsi untuk mengambil data volume kiriman"""
    try:
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)[db_key]
        
        url = f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config.get('port', 3306)}/{config['database']}"
        engine = create_engine(url)



        query_4="""
    
        SELECT 
    o.bulan,
		now() as waktu,
    o.cabang,
		o.normal_kg,
		o.urgent_kg,
		o.top_urgent_kg,
		o.darat_kg,
    o.outbound_kg_reg,
		o.outbound_kg_mtx,
		o.total_outbound_kg,
		o.trip_trucking,
    i.inbound_kg
FROM
(
    -- Subquery untuk outbound
    SELECT 
        bulan, 
        asal_new AS cabang,
				SUM(CASE WHEN (kdproduk='N' AND reg_mtx='REG')THEN berat ELSE 0 END) AS normal_kg,
				SUM(CASE WHEN (kdproduk='U' AND reg_mtx='REG') THEN berat ELSE 0 END) AS urgent_kg,
				SUM(CASE WHEN (kdproduk='T' AND reg_mtx='REG')THEN berat ELSE 0 END) AS top_urgent_kg,
				SUM(CASE WHEN (kdproduk='D' AND reg_mtx='REG') THEN berat ELSE 0 END) AS darat_kg, 
        SUM(CASE WHEN (kdproduk IN ('N', 'U', 'T', 'D') AND reg_mtx='REG') THEN berat ELSE 0 END) AS outbound_kg_reg,
				sum(case when (kdproduk in ('N', 'U', 'T', 'D') and reg_mtx ='MTX') then berat else 0 end) as outbound_kg_mtx,
				sum(case when kdproduk in ('N', 'U', 'T', 'D') then berat else 0 end) as total_outbound_kg,			
				sum(case when kdproduk='C' then 1 else 0 end) as trip_trucking

    FROM
    (
        -- Data pengiriman keluar
        SELECT 
            DATE_FORMAT(tanggal, "%b-%y") AS bulan, tanggal,
            konid, kdpelanggan,
            pengirim, penerima, tujuan,
            kdproduk, asal, 
            if(left(kdpelanggan,3) in ('CTG','CBK', 'CBO'),'CBH', left(kdpelanggan,3) ) AS asal_new,
						IF(left(kdpelanggan,3)= IF(asal='CBM', 'CBH', asal),'REG','MTX') as reg_mtx,
            koli, berat, kdmani, 
            IF(kdmani IN ('RAX', 'REX', 'CLT', 'SAP'), 'CBD', Kdmani) AS kdmani_new,
            awbno, 
						createdby
        FROM tkonos
        WHERE tanggal >= '2025-09-01' AND tanggal <= NOW()
            AND kdpelanggan NOT LIKE 'CBD18002%'
            and kdpelanggan NOT LIKE 'CSG18002%'
            and kdpelanggan NOT LIKE 'CSB18002%'
            and kdpelanggan NOT LIKE 'CBH17002%'
            and kdpelanggan NOT LIKE 'CML18002%'
            and kdpelanggan NOT LIKE 'CDP18002%'
						#and left(kdpelanggan,3) ='CML'
						#and IF(left(kdpelanggan,3)= IF(asal='CBM', 'CBH', asal),'REG','MTX')='MTX'
            AND left(kdpelanggan,3) IN ('CBH','CBM','CBD', 'CSB', 'CSG', 'CML', 'CDP', 'CBK','CBO','CTG')
    ) AS new1
    GROUP BY bulan, asal_new
		
) AS o
LEFT JOIN
(
    -- Subquery untuk inbound
    SELECT 
        bulan, 
        kdmani_new AS cabang,
        SUM(CASE WHEN kdproduk IN ('N', 'U', 'T', 'D') THEN berat ELSE 0 END) AS inbound_kg
    FROM
    (
        -- Data penerimaan masuk
        SELECT 
            DATE_FORMAT(tanggal, "%b-%y") AS bulan,
            konid, kdpelanggan, nott,           
            jenis, tanggal, pengirim, penerima, tujuan,
            kdproduk, asal, 
            IF(asal='CBM', 'CBH', asal) AS asal_new,
            koli, berat, kdmani,
            IF(kdmani IN ('RAX', 'REX', 'CLT', 'SAP'), 'CBD', 
               IF(kdmani IN ('CBK', 'CBO', 'CTG'), 'CBH', kdmani)) AS kdmani_new,
            awbno, createdby
        FROM tkonos
        WHERE tanggal >= '2025-09-01' AND tanggal <= NOW()
            AND kdpelanggan NOT LIKE 'CBD18002%'
            AND kdpelanggan NOT LIKE 'CSG18002%'
            AND kdpelanggan NOT LIKE 'CSB18002%'
            AND kdpelanggan NOT LIKE 'CBH17002%'
            AND kdpelanggan NOT LIKE 'CML18002%'
            AND kdpelanggan NOT LIKE 'CDP18002%'         
    ) AS new2
    GROUP BY bulan, kdmani_new
) AS i
ON o.bulan = i.bulan AND o.cabang = i.cabang;

            
            
    """


        with engine.connect() as conn:
            df = pd.read_sql(query_4, conn)
        
        return df
        
    except Exception as e:
        print(f"ERROR DATABASE (fetch_volume_data): {e}")
        return pd.DataFrame()





#============ GeoJSON ========#



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
                        '96_papua_barat_daya.geojson','34_DIY.geojson'
                        

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
        nama_prov = gdf['provinsi'].iloc[0]
      
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


        #st.markdown("### 📅 Pilih Bulan:")
              
        st.markdown("""<h6 style='font-size: 20px; color: #1565C0; 
                    display: flex; align-items: center; margin-top: 10px; margin-bottom: 0px;             
                    '> 📅 Pilih Bulan:</h6>""", 
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

        

    
    if df.empty:
        st.warning("Tidak ada data untuk ditampilkan.")
        return st.container()

    with row1_col2:

         
        all= f"{len(datafr)} Kiriman"
        dok_pkt= f""" {len(dok_qty)} Dokumen + {len(pkt_qty)} Paket """


        st.markdown(f""" <div style='
        border: 2px solid #1565C0;
        padding: 5px;
        margin: 5px;
        display: inline-block;
        border-radius: 0px;'>
                    <h4 style='font-size: 26px; margin-top: 10px; margin-left: 20px; color: #1565C0;'>{all} : {dok_pkt} </h4> """, 
            unsafe_allow_html=True, text_alignment="center")   
        

       


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
        #rename_map = {'N': 'Normal', 'U': 'Urgent', 'T': 'Top Urgent', 
        #              'D': 'Darat', 'C': 'Trucking', 'P': 'Premium'}
        #pivot_2c.rename(columns=rename_map, inplace=True)
        
        


        # Urutkan kolom sesuai keinginan (Darat, Normal, Urgent, Top Urgent)
        #urutan_kolom = ['Darat', 'Normal', 'Urgent', 'Top Urgent', 'Trucking', 'Premium']
        
        
        # Hanya ambil kolom yang ADA di dataframe
        #kolom_ada = [col for col in urutan_kolom if col in pivot_2c.columns]

        # Urutkan dataframe dengan kolom yang ada
        #pivot_2c = pivot_2c[kolom_ada]


        # Rename kolom produk
        rename_map = {'N': 'Normal', 'U': 'Urgent', 'T': 'Top Urgent', 
              'D': 'Darat', 'C': 'Trucking', 'P': 'Premium'}
        pivot_2c.rename(columns=rename_map, inplace=True)

        # URUTAN YANG DIINGINKAN
        urutan_kolom = ['Darat', 'Normal', 'Urgent', 'Top Urgent', 'Trucking', 'Premium']

        # SOLUSI 2: REINDEX DENGAN FILL_VALUE=0
        pivot_2c = pivot_2c.reindex(columns=urutan_kolom, fill_value=0)

        # Hitung total
        pivot_2c['sum'] = pivot_2c.sum(axis=1)
        final = pivot_2c.sort_values("sum", ascending=False).head(11)
        st.dataframe(final)





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
            margin=(25, 0, 0, 0),
            
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
        text= f"Kiriman Belum Ada Status dari {top} Pelanggan Teratas",
        align="left",
        text_font_size="12pt",
        text_font_style="bold",
        text_color="#36454F",
        background_fill_color="#f0f0f0",
        background_fill_alpha=0.15,
        
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
        ph.legend.border_line_alpha = 0.15

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
            top_1=len(listkdmani)
            
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
                margin=(25, 0, 0, 0),  # (top, right, bottom, left) dalam pixel
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
            text= f"Kiriman Belum Ada Status di {top_1} Cabang/Agen Teratas",
            align="center",
            text_font_size="12pt",
            #text_font_style="bold",
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
        fig.update_layout(dragmode=False, title_x=0.24, title_y=0.95, title_font_size=20, title_font_color="#0E0E0F", 
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



 



def page_2():
    return st.container()



def page_3():

    from bokeh.transform import dodge
    from bokeh.models import NumeralTickFormatter
    from bokeh.models import HoverTool
    df = fetch_data2()
    #st.dataframe(df)


    df.columns= ["tahun","bulan" ,"bln_thn", "qty_pcs", "berat_kg"]
    df["qty_pcs"] = df[["qty_pcs"]].astype(int)
    df["berat_kg"] = df[["berat_kg"]].astype(int)

    df2024 = pd.read_csv('data/vol2024_2025_streamlit.csv', sep=',')
    df_combined = pd.concat([df2024, df], ignore_index=True)
    
    #st.dataframe(datapage3)

    data2024=df_combined[df_combined["tahun"]==2024]
    data2025=df_combined[df_combined["tahun"]==2025]
    data2026=df_combined[df_combined["tahun"]==2026]

    bulanku = df_combined['bulan'].unique().tolist()
    tahunku = df_combined['tahun'].unique().tolist()

    #bln_thn_all=df_combined["bln_thn"].to_list()
    #berat_all = df_combined["berat_kg"].to_list()

    berat_2024=data2024["berat_kg"].to_list()
    berat_2025=data2025["berat_kg"].to_list()
    berat_2026=data2026["berat_kg"].to_list()

 
    list_b = [0] * (12 -len(berat_2026))
    berat_2026.extend(list_b)  # to make sure the length matches for plotting







    fruits = bulanku
    #years = tahunku

    dataku = {'fruits' : fruits,
        '2024'   : berat_2024,
        '2025'   : berat_2025,
        '2026'   : berat_2026}

    source = ColumnDataSource(dataku)

    hover = HoverTool(
    tooltips=[
        ("Bulan", "@fruits"),
        ("2024", "@2024{0,0}"),
        ("2025", "@2025{0,0}"),
        ("2026", "@2026{0,0}"),],
          #formatters= {'@2024': 'printf', '@2025': 'printf', '@2026': 'printf'}, 
          )



    
    pgab = figure(x_range=bulanku, y_range=(0, 200000), 
                  title="Volume Berat Kiriman per Bulan Tahun 2024 - 2026",
                  height=350, width=1200, toolbar_location=None, )
    

    pgab.vbar(x=dodge('fruits', -0.30, range=pgab.x_range), top='2024', source=source,
       width=0.28, color="#daf3ea", legend_label="2024")

    pgab.vbar(x=dodge('fruits',  0.0,  range=pgab.x_range), top='2025', source=source,
       width=0.28, color="#718dbf", legend_label="2025")

    pgab.vbar(x=dodge('fruits',  0.30, range=pgab.x_range), top='2026', source=source,
       width=0.28, color="#e84d61", legend_label="2026")

    pgab.x_range.range_padding = 0.05
    pgab.xgrid.grid_line_color = None
    pgab.legend.location = "top_left"
    pgab.legend.orientation = "horizontal"
    pgab.yaxis.formatter = NumeralTickFormatter(format="0,0")
    pgab.add_tools(hover)
    #pgab.axis_label_text_font_size = '10px'

    streamlit_bokeh(pgab)








    #return st.container()

def page_4():

    #datapage4 = fetch_data3(df, "mysql02")
    df = fetch_data3()

    st.dataframe(df)



    #datapage4.columns = ['bulan', 'waktu', 'cabang','normal_kg', 'urgent_kg', 'top_urgent_kg', 'darat_kg', 'reg_kg', 'matrix_kg', 'total_kg','trip_trucking', 'inbound_kg']

    #datapage4["cabang"] = datapage4[["cabang"]].astype(str)
    #datapage4["normal_kg"] = datapage4[["normal_kg"]].astype(int)
    #datapage4["urgent_kg"] = datapage4[["urgent_kg"]].astype(int)
    #datapage4["top_urgent_kg"] = datapage4[["top_urgent_kg"]].astype(int)
    #datapage4["darat_kg"] = datapage4[["darat_kg"]].astype(int)
    #datapage4["reg_kg"] = datapage4[["reg_kg"]].astype(int)
    #datapage4["total_kg"] = datapage4[["total_kg"]].astype(int)
    #datapage4["matrix_kg"] = datapage4[["matrix_kg"]].astype(int)
    #datapage4["trip_trucking"] = datapage4[["trip_trucking"]].astype(int)
    #datapage4["inbound_kg"] = datapage4[["inbound_kg"]].astype(int)
    #datapage4.style.hide(axis="index")
    
    #datapage4= datapage4.drop('waktu', axis=1) # axis=1 specifies column
    #datapage4.reset_index(drop=True, inplace=True)
   
    #import st_aggid
    #from st_aggrid import AgGrid, GridOptionsBuilder

    
    

   
    #lst_cab=datapage4["cabang"].drop_duplicates().sort_index(ascending=True)
    #pilihan4=st.selectbox("Pilih Cabang", lst_cab, key="cabang")  
    
    

    
    #col1, col2 = st.columns([2, 10], gap="small")
    #col3, col4 = st.columns([10, 2], gap="small")



    col1, col2 = st.columns([2, 10], gap="small")
    col3, col4 = st.columns([10, 2], gap="small")

    #with col1:

        #st.text(lst_cab)
        #pil_cab=st.selectbox(label="**Pilih Cabang:**",options= lst_cab)

        #st.dataframe(datapage4[[datapage4.cabang==lst_cab]])
        #filter_dp4=datapage4[(datapage4.cabang==pil_cab)]

        #filter_dp4.reset_index(drop=True, inplace=True)


    #with col3:
            
        #st.dataframe(filter_dp4, hide_index=True)
        #st.dataframe(filter_dp4.style.hide(axis="index"))
    


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