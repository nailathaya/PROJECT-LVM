# """
# Peta Potensi Merchant - Pulogadung (versi sederhana, 2 halaman).

#     pip install streamlit folium streamlit-folium scikit-learn pandas numpy openpyxl
#     streamlit run app_peta_merchant.py

# Taruh di folder yang sama:
#     merchant_geocoded_filtered.csv   (atau merchant_df_area_pulogadung_filtered.csv; harus punya kolom latitude & longitude)
#     poi_filtered.csv                 (osm_key, nama, kategori, latitude, longitude)
# Atau upload lewat sidebar > "Ganti / upload data".
# """

# import datetime as dt
# import html
# import io
# import os

# import folium
# import numpy as np
# import pandas as pd
# import streamlit as st
# from folium.plugins import HeatMap
# from sklearn.neighbors import BallTree
# from streamlit_folium import st_folium

# st.set_page_config(page_title="Peta Potensi Merchant", layout="wide")

# st.markdown(
#     """
#     <style>
#     .block-container {padding-top: 1.4rem; padding-bottom: 1rem;}
#     div[data-testid="stMetric"] {
#         background: rgba(128,128,128,0.10); border: 1px solid rgba(128,128,128,0.28);
#         border-radius: 12px; padding: 12px 16px;
#     }
#     .kartu {border: 1px solid rgba(128,128,128,0.35); border-radius: 12px; padding: 10px 12px; margin-bottom: 10px;}
#     .nomor {display: inline-block; background: #1971c2; color: #fff; border-radius: 50%; width: 26px; height: 26px;
#             text-align: center; line-height: 26px; margin-right: 8px; font-weight: 700; font-size: 0.9rem;}
#     .kecil {opacity: 0.7; font-size: 0.85rem;}
#     .legend span.dot {font-size: 20px; vertical-align: middle;}
#     .legend {margin: 4px 0 8px 0; line-height: 2;}
#     .badge {display: inline-block; background: #1971c2; color: #fff; border-radius: 50%; width: 20px; height: 20px;
#             text-align: center; line-height: 20px; font-size: 11px; font-weight: 700; vertical-align: middle;}
#     .gradbar {height: 12px; border-radius: 6px; background: linear-gradient(90deg, #ffffb2, #fd8d3c, #bd0026);}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# MERCHANT_FILES = ["merchant_geocoded_filtered.csv"]
# DEFAULT_POI = "poi_filtered.csv"
# EARTH = 6371000.0
# GEO_OK = ["ok", "fallback_1", "fallback_2"]
# DATA_DATE = dt.date(2026, 11, 16)     # tanggal tarikan data; kolom *_ytd dihitung sampai tanggal ini
# ZOOM_FOKUS = 17          # level zoom peta saat titik potensial diklik

# STATUS_ORDER = ["Aktif", "Menurun", "Tidak aktif"]
# STATUS_COLOR = {"Aktif": "#2f9e44", "Menurun": "#f08c00", "Tidak aktif": "#e03131"}

# # Jenis tempat yang dianggap "jangkar" (penarik keramaian) beserta namanya dalam bahasa Indonesia.
# KAT_ID = {
#     "school": "Sekolah", "kindergarten": "TK / PAUD", "college": "Perguruan tinggi", "university": "Universitas",
#     "industrial": "Kawasan industri", "factory": "Pabrik", "works": "Pabrik", "warehouse": "Gudang",
#     "company": "Perusahaan", "office": "Kantor", "commercial": "Area komersial", "marketplace": "Pasar",
#     "mall": "Mal", "supermarket": "Supermarket", "department_store": "Toserba", "retail": "Area ritel",
#     "hospital": "Rumah sakit", "clinic": "Klinik", "bus_station": "Terminal / halte", "government": "Kantor pemerintah",
#     "community_centre": "Balai warga", "stadium": "Stadion", "sports_centre": "Pusat olahraga", "hotel": "Hotel",
#     "apartment": "Apartemen",
# }

# NOISE = {
#     "parking", "parking_entrance", "parking_space", "motorcycle_parking", "track", "toilets", "fountain",
#     "water", "ticket_validator", "bicycle_repair_station", "grave_yard", "garden", "playground",
#     "horse_riding", "artwork", "outdoor", "alternative", "oil", "it", "social_facility",
# }
# GROUPS = {
#     "Pendidikan": ["school", "kindergarten", "prep_school", "college", "university", "educational_institution", "language_school", "library"],
#     "Tempat ibadah": ["place_of_worship"],
#     "Pemerintahan": ["government", "police", "fire_station", "military", "administrative", "post_office", "political_party", "community_centre"],
#     "Kesehatan": ["hospital", "clinic", "pharmacy", "doctors", "dentist", "midwife", "chemist", "medical_supply", "veterinary"],
#     "Industri & gudang": ["industrial", "factory", "warehouse", "works", "logistics", "depot", "storage_rental"],
#     "Kantor & komersial": ["company", "office", "commercial", "estate_agent", "insurance_agent"],
#     "Pasar & retail": ["marketplace", "mall", "supermarket", "department_store", "retail", "convenience", "general", "variety_store",
#                        "hardware", "doityourself", "kiosk", "greengrocer", "grocery", "clothes", "shoes", "electronics",
#                        "mobile_phone", "copyshop", "stationery"],
#     "Kuliner": ["restaurant", "fast_food", "cafe", "coffee", "food_court", "ice_cream", "pub", "bar", "bakery", "pastry",
#                 "chocolate", "beverages", "frozen", "alcohol"],
#     "Transportasi & otomotif": ["bus_station", "fuel", "charging_station", "car_repair", "car_wash", "car_parts", "car", "motorcycle", "bicycle"],
#     "Bank & keuangan": ["bank", "atm", "bureau_de_change"],
#     "Olahraga & rekreasi": ["park", "sports_centre", "sports", "pitch", "stadium", "swimming_pool", "fitness_centre", "golf_course",
#                             "cinema", "amusement_arcade", "nightclub"],
#     "Penginapan": ["hotel", "guest_house", "apartment"],
# }
# CAT2GROUP = {c: g for g, cats in GROUPS.items() for c in cats}


# # ---------------- Fungsi bantu ----------------
# def esc(x):
#     return html.escape(str(x))


# def guess(columns, candidates):
#     lower = {c.lower().strip(): c for c in columns}
#     for name in candidates:
#         if name in lower:
#             return lower[name]
#     return None


# def read_file(f):
#     if f.name.lower().endswith(".csv"):
#         return pd.read_csv(f)
#     return pd.read_excel(f)


# def rad(lat, lon):
#     return np.radians(np.column_stack([np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)]))


# def count_within(q, t, r_m):
#     if len(t) == 0:
#         return np.zeros(len(q), dtype=int)
#     return BallTree(t, metric="haversine").query_radius(q, r=r_m / EARTH, count_only=True)


# def near(p_lat, p_lon, m_lat, m_lon, r_m, excl_m):
#     """Jumlah merchant dalam r_m dari tiap POI. Merchant dalam excl_m meter (kemungkinan usaha yang sama dengan POI) tidak dihitung."""
#     q, t = rad(p_lat, p_lon), rad(m_lat, m_lon)
#     c = count_within(q, t, r_m)
#     if excl_m > 0:
#         c = c - count_within(q, t, excl_m)
#     return np.clip(c, 0, None)


# def gmaps(lat, lon):
#     return "https://www.google.com/maps?q=" + str(lat) + "," + str(lon)


# def pilih_tersebar(cand, n, min_sep_m):
#     """Ambil n kandidat teratas yang saling berjauhan (min_sep_m) dan bervariasi: jumlah titik dari satu kelompok
#     jenis tempat dibatasi, supaya daftar tidak didominasi satu jenis saja (mis. rumah sakit atau mal)."""
#     if cand.empty:
#         return cand
#     lat = np.radians(cand["latitude"].to_numpy())
#     lon = np.radians(cand["longitude"].to_numpy())
#     grp = cand["kelompok"].to_numpy()
#     cap = max(2, int(np.ceil(n / 4)))

#     def jauh_dari_terpilih(i, chosen):
#         if not chosen:
#             return True
#         c = np.array(chosen)
#         a = np.sin((lat[c] - lat[i]) / 2) ** 2 + np.cos(lat[i]) * np.cos(lat[c]) * np.sin((lon[c] - lon[i]) / 2) ** 2
#         return not (2 * EARTH * np.arcsin(np.sqrt(a)) < min_sep_m).any()

#     chosen, count = [], {}
#     for batas in (cap, None):      # putaran 1: dengan batas per kelompok; putaran 2: isi sisa tanpa batas
#         for i in range(len(cand)):
#             if len(chosen) >= n:
#                 break
#             if i in chosen or (batas is not None and count.get(grp[i], 0) >= batas):
#                 continue
#             if jauh_dari_terpilih(i, chosen):
#                 chosen.append(i)
#                 count[grp[i]] = count.get(grp[i], 0) + 1
#     chosen.sort()                  # pertahankan urutan prioritas
#     return cand.iloc[chosen]


# def set_fokus(lat, lon):
#     st.session_state["fokus"] = (float(lat), float(lon))


# def reset_fokus():
#     st.session_state["fokus"] = None


# # ---------------- Sidebar ----------------
# st.sidebar.title("Peta Potensi Merchant")
# with st.sidebar.expander("Ganti / upload data"):
#     mfile = st.file_uploader("Data merchant (CSV / Excel)", type=["csv", "xlsx", "xls"])
#     pfile = st.file_uploader("Data POI OSM (CSV)", type=["csv"])
#     rfile = st.file_uploader("Hasil model building_potensi.csv (opsional)", type=["csv"])

# raw, src = None, None
# try:
#     if mfile is not None:
#         raw, src = read_file(mfile), mfile.name
#     else:
#         for fn in MERCHANT_FILES:
#             if os.path.exists(fn):
#                 raw, src = pd.read_csv(fn), fn
#                 break
# except Exception as e:
#     st.sidebar.error("File merchant tidak bisa dibaca: " + str(e))

# if raw is None:
#     st.title("Peta Potensi Merchant")
#     st.info("Data merchant belum ditemukan. Taruh `" + MERCHANT_FILES[0] + "` di folder yang sama dengan aplikasi ini, "
#             "atau upload lewat sidebar > Ganti / upload data.")
#     st.stop()
# cols = list(raw.columns)

# poi_raw = None
# try:
#     if pfile is not None:
#         poi_raw = pd.read_csv(pfile)
#     elif os.path.exists(DEFAULT_POI):
#         poi_raw = pd.read_csv(DEFAULT_POI)
# except Exception as e:
#     st.sidebar.error("File POI tidak bisa dibaca: " + str(e))

# lat_col = guess(cols, ["latitude", "lat", "lintang", "geo_lat"])
# lon_col = guess(cols, ["longitude", "lon", "lng", "long", "bujur", "geo_lon"])
# if not lat_col or not lon_col:
#     st.title("Peta Potensi Merchant")
#     st.error("Data merchant belum punya kolom koordinat (latitude dan longitude), jadi belum bisa dipetakan.")
#     st.markdown(
#         "Kolom yang terbaca: `" + "`, `".join(cols[:25]) + "`" + (" ..." if len(cols) > 25 else "") + "\n\n"
#         "**Langkah:** lakukan geocoding kolom `address` dulu, simpan hasilnya sebagai CSV yang memuat kolom `latitude` dan "
#         "`longitude` (serta `geocode_status` bila ada), lalu taruh di folder ini atau upload di sidebar."
#     )
#     st.stop()

# geo_col = guess(cols, ["geocode_status"])
# id_col = guess(cols, ["store_id", "merchant_id", "mid", "id"])
# nama_col = guess(cols, ["store_name", "nama_merchant", "nama", "name"])
# kat_col = guess(cols, ["lob_lm", "kategori", "category", "jenis_usaha"])
# cab_col = guess(cols, ["nama_cabang_final", "cabang", "branch"])
# f30_col = guess(cols, ["freq_30_days", "frek_30", "trx_30"])
# s30_col = guess(cols, ["sv_30_days", "sales_30", "nominal_30"])
# fytd_col = guess(cols, ["freq_ytd", "frek_ytd", "trx_ytd"])
# sytd_col = guess(cols, ["sv_ytd", "sales_ytd", "nominal_ytd"])

# with st.sidebar.expander("Pengaturan lanjutan"):
#     st.caption("Biasanya tidak perlu diubah.")
#     data_date = st.date_input("Tanggal tarikan data (YTD sampai tanggal ini)", DATA_DATE)
#     months = max(1.0, ((data_date - dt.date(data_date.year, 1, 1)).days + 1) / (365.25 / 12))
#     st.caption("Rata-rata bulanan YTD dihitung dengan " + format(months, ".1f") + " bulan.")
#     min_active = st.number_input("Minimal transaksi 30 hari agar disebut Aktif", 1, 1000, 20)
#     min_sales = st.number_input("Sales 30 hari agar disebut Aktif harus lebih dari", 0, 10**12, 100000, 10000)
#     drop_pct = st.slider("Penurunan dianggap tajam (%)", 10, 90, 50)
#     r_m = st.slider("Radius jangkar (meter)", 100, 500, 300, 50)
#     min_sep =st.slider("Jarak minimal antar titik potensial (meter)", 100, 1000, 300, 50)
#     min_eks = st.number_input("Merchant yang 'biasanya' ada di tempat serupa, minimal", 0.0, 50.0, 1.0, 0.5)
#     only_geo_ok = st.checkbox("Hanya titik geocode yang layak", value=True, disabled=geo_col is None)

# if not geo_col:
#     only_geo_ok = False


# # ---------------- Susun data merchant ----------------
# def num(c):
#     if c:
#         return pd.to_numeric(raw[c], errors="coerce").fillna(0)
#     return pd.Series(0.0, index=raw.index)


# def text(c, default):
#     if c:
#         return raw[c].fillna("-").astype(str)
#     return pd.Series(default, index=raw.index)


# f30, fytd = num(f30_col), num(fytd_col)
# avg_month = fytd / months
# sharp = (avg_month > 0) & (f30 < avg_month * (1 - drop_pct / 100))
# s30 = num(s30_col)
# low_sales = (s30 <= min_sales) if s30_col else False
# low = (f30 > 0) & ((f30 < min_active) | low_sales)      # ada transaksi, tapi belum memenuhi ambang Aktif
# status = np.select([f30 <= 0, sharp | low], [STATUS_ORDER[2], STATUS_ORDER[1]], default=STATUS_ORDER[0])

# df = pd.DataFrame(
#     {
#         "id": raw[id_col].astype(str) if id_col else raw.index.astype(str),
#         "nama": text(nama_col, "(tanpa nama)"),
#         "kategori": text(kat_col, "-"),
#         "cabang": text(cab_col, "-"),
#         "geocode": text(geo_col, "-"),
#         "lat": pd.to_numeric(raw[lat_col], errors="coerce"),
#         "lon": pd.to_numeric(raw[lon_col], errors="coerce"),
#         "frek_30": f30,
#         "sv_30": s30,
#         "frek_ytd": fytd,
#         "sv_ytd": num(sytd_col),
#         "status": status,
#     }
# )
# n_raw = len(df)
# df = df.dropna(subset=["lat", "lon"])
# df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]
# if only_geo_ok:
#     df = df[df["geocode"].isin(GEO_OK)]
# if df.empty:
#     st.error("Tidak ada titik koordinat yang layak untuk dipetakan.")
#     st.stop()
# st.sidebar.caption("Merchant: " + src + " | dipetakan " + format(len(df), ",") + " dari " + format(n_raw, ",") + " baris")

# # ---------------- Siapkan POI ----------------
# poi = None
# if poi_raw is not None:
#     if {"latitude", "longitude", "kategori"}.issubset(set(poi_raw.columns)):
#         poi = poi_raw.copy()
#         poi["latitude"] = pd.to_numeric(poi["latitude"], errors="coerce")
#         poi["longitude"] = pd.to_numeric(poi["longitude"], errors="coerce")
#         poi = poi.dropna(subset=["latitude", "longitude", "kategori"])
#         poi = poi[~poi["kategori"].isin(NOISE)].reset_index(drop=True)
#         if "nama" not in poi.columns:
#             poi["nama"] = ""
#         poi["nama"] = poi["nama"].fillna("").astype(str)
#         if "osm_key" not in poi.columns:
#             poi["osm_key"] = "idx/" + poi.index.astype(str)
#         poi["kelompok"] = poi["kategori"].map(CAT2GROUP).fillna("Lainnya")
#         if poi.empty:
#             poi = None
#     else:
#         st.sidebar.error("File POI harus punya kolom: latitude, longitude, kategori.")

# # ---------------- Hitung kandidat titik potensial ----------------
# cand = pd.DataFrame()
# ref_table = None
# alasan_kosong = ""
# if poi is None:
#     alasan_kosong = "Data POI (poi_filtered.csv) belum tersedia."
# elif len(df) < 30:
#     alasan_kosong = "Merchant yang dipetakan kurang dari 30, terlalu sedikit untuk membandingkan."
# else:
#     base = poi.copy()
#     base["merchant_sekitar"] = near(base["latitude"].to_numpy(), base["longitude"].to_numpy(),
#                                     df["lat"].to_numpy(), df["lon"].to_numpy(), r_m, 30)
#     mu_all = float(base["merchant_sekitar"].mean())
#     g = base.groupby("kategori")["merchant_sekitar"].agg(["sum", "count"])
#     mu = (g["sum"] + 10 * mu_all) / (g["count"] + 10)       # rata-rata sekategori, disusutkan ke rata-rata umum
#     base["biasanya"] = base["kategori"].map(mu)
#     pakai_model = False
#     if rfile is not None:
#         try:
#             res = pd.read_csv(rfile)
#             if {"osm_key", "ekspektasi"}.issubset(set(res.columns)):
#                 base = base.merge(res[["osm_key", "ekspektasi"]], on="osm_key", how="left")
#                 base["biasanya"] = base["ekspektasi"].fillna(base["biasanya"])
#                 pakai_model = True
#             else:
#                 st.sidebar.warning("File hasil model harus punya kolom osm_key dan ekspektasi.")
#         except Exception as e:
#             st.sidebar.warning("File hasil model tidak bisa dibaca: " + str(e))
#     base["selisih"] = base["biasanya"] - base["merchant_sekitar"]
#     base["skor"] = base["selisih"] / np.sqrt(base["biasanya"].clip(lower=1))   # selisih relatif terhadap skala jenis tempatnya
#     base["jenis"] = base["kategori"].map(KAT_ID)
#     ref_table = (
#         base[base["jenis"].notna()].groupby("jenis")
#         .agg(**{"Jumlah tempat": ("kategori", "size"), "Rata-rata merchant sekitar": ("merchant_sekitar", "mean"),
#                 "Biasanya": ("biasanya", "mean")})
#         .round(1).sort_values("Jumlah tempat", ascending=False).reset_index().rename(columns={"jenis": "Jenis tempat"})
#     )
#     cand = base[base["jenis"].notna() & (base["selisih"] > 0) & (base["biasanya"] >= min_eks)]
#     cand = cand.sort_values(["skor", "selisih"], ascending=False)
#     if cand.empty:
#         alasan_kosong = "Tidak ada jangkar yang merchant-nya jauh di bawah kebiasaan tempat serupa dengan pengaturan sekarang."

# # ---------------- Judul & ringkasan ----------------
# st.title("Peta Potensi Merchant - Pulogadung")
# # st.caption("Lihat di mana merchant sudah ada, dan di titik mana (sekolah, pabrik, pasar, dll) merchant masih jauh lebih sedikit dari seharusnya.")

# total = len(df)
# n_aktif = int((df["status"] == "Aktif").sum())
# k1, k2, k3, k4 = st.columns(4)
# k1.metric("Total merchant", format(total, ","))
# k2.metric("Aktif", format(n_aktif, ","), format(n_aktif / total * 100, ".0f") + "% dari total", delta_color="off")
# k3.metric("Perlu ditindaklanjuti", format(total - n_aktif, ","), "menurun atau tidak aktif", delta_color="off")
# sales_30 = float(df["sv_30"].sum())
# k4.metric("Sales 30 hari", format(sales_30 / 1e6, ",.1f") + " M", format(sales_30, ",.0f"), delta_color="off")

# tab_peta, tab_daftar = st.tabs(["Peta", "Daftar kunjungan"])

# # ============================ HALAMAN 1: PETA ============================
# with tab_peta:
#     c1, c2, c3, c4 = st.columns([1, 1.3, 1.5, 2])
#     show_m = c1.checkbox("Merchant", value=True)
#     show_p = c2.checkbox("Titik potensial", value=True, disabled=cand.empty)
#     show_h = c3.checkbox("Kepadatan merchant", value=True, help="Warna hangat = banyak merchant yang SUDAH ada. Bukan potensi.")
#     n_pot = c4.slider("Jumlah titik potensial", 5, 30, 10)

#     sel = pilih_tersebar(cand, n_pot, min_sep) if not cand.empty else cand

#     legend = " &nbsp;&nbsp; ".join(
#         "<span class='dot' style='color:" + STATUS_COLOR[s] + "'>&#9679;</span> Merchant " + s.lower() for s in STATUS_ORDER
#     )
#     legend += " &nbsp;&nbsp; <span class='badge'>1</span> Titik potensial (urut prioritas)"
#     st.markdown("<div class='legend'>" + legend + "</div>", unsafe_allow_html=True)

#     left, right = st.columns([3, 1.35])

#     with left:
#         fokus = st.session_state.get("fokus")
#         center = [df["lat"].mean(), df["lon"].mean()]
#         m = folium.Map(location=list(fokus) if fokus else center, zoom_start=ZOOM_FOKUS if fokus else 14,
#                        tiles="OpenStreetMap", control_scale=True)

#         if show_h:
#             HeatMap(df[["lat", "lon"]].values.tolist(), radius=25, blur=20, min_opacity=0.3,
#                     gradient={0.2: "#ffffb2", 0.5: "#fd8d3c", 1.0: "#bd0026"}).add_to(m)

#         if show_m:
#             for r in df.itertuples():
#                 color = STATUS_COLOR[r.status]
#                 popup = (
#                     "<b>" + esc(r.nama) + "</b><br>" + esc(r.kategori) + "<br>Status: <b>" + r.status + "</b>"
#                     + "<br>Transaksi 30 hari: " + format(r.frek_30, ",.0f")
#                     + "<br>Sales 30 hari: " + format(r.sv_30, ",.0f")
#                     + "<br><a href='" + gmaps(r.lat, r.lon) + "' target='_blank'>Buka di Google Maps</a>"
#                 )
#                 folium.CircleMarker(
#                     location=[r.lat, r.lon], radius=5, color="#ffffff", weight=1, fill=True, fill_color=color,
#                     fill_opacity=0.9, tooltip=esc(r.nama) + " - " + r.status, popup=folium.Popup(popup, max_width=280),
#                 ).add_to(m)

#         if show_p and not sel.empty:
#             for rank, r in enumerate(sel.itertuples(), 1):
#                 judul = r.nama if r.nama.strip() else r.jenis + " (tanpa nama)"
#                 popup = (
#                     "<b>#" + str(rank) + " " + esc(judul) + "</b><br>" + esc(r.jenis)
#                     + "<br>Merchant dalam " + str(r_m) + " m: <b>" + format(r.merchant_sekitar, ",.0f") + "</b>"
#                     + "<br>Tempat serupa biasanya: <b>" + format(r.biasanya, ".0f") + "</b>"
#                     + "<br><a href='" + gmaps(r.latitude, r.longitude) + "' target='_blank'>Buka di Google Maps</a>"
#                 )
#                 folium.Circle(
#                     location=[r.latitude, r.longitude], radius=r_m, color="#1971c2", weight=2, dash_array="6",
#                     fill=True, fill_color="#1971c2", fill_opacity=0.10,
#                 ).add_to(m)
#                 badge = (
#                     "<div style='background:#1971c2;color:#fff;border:2px solid #fff;border-radius:50%;width:30px;height:30px;"
#                     "line-height:26px;text-align:center;font-weight:700;font-size:14px;box-shadow:0 1px 5px rgba(0,0,0,.55)'>"
#                     + str(rank) + "</div>"
#                 )
#                 folium.Marker(
#                     location=[r.latitude, r.longitude],
#                     icon=folium.DivIcon(html=badge, icon_size=(30, 30), icon_anchor=(15, 15)),
#                     tooltip="#" + str(rank) + " " + esc(judul), popup=folium.Popup(popup, max_width=300),
#                 ).add_to(m)

#         pts_lat = list(df["lat"]) + (list(sel["latitude"]) if show_p and not sel.empty else [])
#         pts_lon = list(df["lon"]) + (list(sel["longitude"]) if show_p and not sel.empty else [])
#         if fokus:
#             st_folium(m, width=None, height=650, returned_objects=[], center=list(fokus), zoom=ZOOM_FOKUS)
#         else:
#             m.fit_bounds([[min(pts_lat), min(pts_lon)], [max(pts_lat), max(pts_lon)]])
#             st_folium(m, width=None, height=650, returned_objects=[])

#         # if show_h:
#         #     st.markdown("<div class='gradbar'></div>", unsafe_allow_html=True)
#         #     st.caption("Kepadatan merchant yang sudah ada: kuning = sedikit, merah = banyak.")
#         # if show_p and not sel.empty:
#         #     st.caption("Lingkaran biru putus-putus = radius " + str(r_m) + " m di sekitar titik potensial.")

#     with right:
#         st.subheader("Titik potensial")
#         if sel.empty:
#             st.info(alasan_kosong or "Belum ada titik potensial.")
#         else:
#             if st.session_state.get("fokus"):
#                 st.button("Kembali ke peta penuh", on_click=reset_fokus, use_container_width=True)
#             with st.container(height=600):
#                 for rank, r in enumerate(sel.itertuples(), 1):
#                     judul = r.nama if r.nama.strip() else r.jenis + " (tanpa nama)"
#                     with st.container(border=True):
#                         teks, tombol = st.columns([5, 1], vertical_alignment="center")
#                         teks.markdown(
#                             "<span class='nomor'>" + str(rank) + "</span><b>" + esc(judul) + "</b><br>"
#                             "<span class='kecil'>" + esc(r.jenis) + "</span><br>"
#                             "<a href='" + gmaps(r.latitude, r.longitude) + "' target='_blank'>Buka di Google Maps</a>",
#                             unsafe_allow_html=True,
#                         )
#                         tombol.button("🔍", key="fokus_" + str(rank), on_click=set_fokus,
#                                       args=(r.latitude, r.longitude), help="Lihat")

#     # with st.expander("Cara membaca"):
#     #     st.markdown(
#     #         "- **Titik potensial** adalah jangkar keramaian (sekolah, pabrik, pasar, kantor, rumah sakit, dll) yang merchant di sekitarnya "
#     #         "**lebih sedikit** daripada tempat sejenis lainnya di area ini. Selisih dinilai relatif terhadap kebiasaan jenis tempatnya "
#     #         "(mal yang biasanya 20 merchant tidak otomatis mengalahkan sekolah yang biasanya 6), dan satu kelompok jenis tempat "
#     #         "dibatasi jumlahnya agar daftar bervariasi. Titik juga dipilih saling berjauhan.\n"
#     #         "- **Merchant** diberi warna: hijau = aktif (minimal " + str(min_active) + " transaksi dan sales lebih dari "
#     #         + format(min_sales, ",.0f") + " dalam 30 hari), oranye = menurun (ada transaksi, tapi di bawah ambang aktif, atau "
#     #         "transaksi turun lebih dari " + str(drop_pct) + "% dari rata-rata bulanan tahun ini), "
#     #         "merah = tidak ada transaksi dalam 30 hari.\n"
#     #         "- Ini perbandingan dengan kebiasaan tempat sejenis, **bukan jaminan** bahwa kunjungan akan menambah registrasi. "
#     #         "Area yang kosong, tertutup, atau sudah dijangkau cabang lain tidak terdeteksi otomatis. Cek di lapangan dan catat hasilnya."
#     #     )

# # ============================ HALAMAN 2: DAFTAR ============================
# with tab_daftar:
#     st.subheader("1. Titik potensial untuk dikunjungi")
#     if sel.empty:
#         st.info(alasan_kosong or "Belum ada titik potensial.")
#     else:
#         t1 = sel.copy().reset_index(drop=True)
#         t1.insert(0, "Prioritas", range(1, len(t1) + 1))
#         t1["Nama"] = [(n if n.strip() else j + " (tanpa nama)") for n, j in zip(t1["nama"], t1["jenis"])]
#         t1["Alasan"] = ["Baru " + format(a, ".0f") + " merchant dalam " + str(r_m) + " m, biasanya sekitar " + format(b, ".0f")
#                         for a, b in zip(t1["merchant_sekitar"], t1["biasanya"])]
#         t1["Peta"] = [gmaps(a, b) for a, b in zip(t1["latitude"], t1["longitude"])]
#         show1 = t1[["Prioritas", "Nama", "jenis", "merchant_sekitar", "biasanya", "Alasan", "Peta"]].rename(
#             columns={"jenis": "Jenis tempat", "merchant_sekitar": "Merchant di sekitar", "biasanya": "Biasanya"})
#         show1["Biasanya"] = show1["Biasanya"].round(0)
#         st.dataframe(show1, hide_index=True, column_config={"Peta": st.column_config.LinkColumn("Peta", display_text="Buka")})
#         out = io.StringIO()
#         show1.to_csv(out, index=False)
#         st.download_button("Unduh daftar titik potensial (CSV)", out.getvalue(), "titik_potensial.csv", "text/csv")

#     st.subheader("2. Merchant yang perlu ditindaklanjuti")
#     st.caption("Diurutkan dari sales YTD terbesar: merchant yang dulu bernilai besar dan sekarang turun atau berhenti ada di atas.")
#     t2 = df[df["status"] != "Aktif"].copy()
#     if t2.empty:
#         st.success("Semua merchant berstatus aktif.")
#     else:
#         t2["Tindakan"] = np.where(
#             t2["status"] == "Menurun", "Kunjungi, tanyakan kendala transaksi",
#             np.where(t2["frek_ytd"] <= 0, "Aktivasi: bantu transaksi pertama", "Hubungi, pastikan usaha masih beroperasi"),
#         )
#         t2["Peta"] = [gmaps(a, b) for a, b in zip(t2["lat"], t2["lon"])]
#         t2 = t2.sort_values("sv_ytd", ascending=False)
#         show2 = t2[["nama", "kategori", "cabang", "status", "frek_30", "sv_ytd", "Tindakan", "Peta"]].rename(
#             columns={"nama": "Nama", "kategori": "Kategori usaha", "cabang": "Cabang", "status": "Status",
#                      "frek_30": "Trx 30 hari", "sv_ytd": "Sales YTD"})
#         st.dataframe(show2.head(200), hide_index=True, column_config={"Peta": st.column_config.LinkColumn("Peta", display_text="Buka")})
#         out = io.StringIO()
#         show2.to_csv(out, index=False)
#         st.download_button("Unduh daftar merchant (CSV)", out.getvalue(), "merchant_tindak_lanjut.csv", "text/csv")

#     st.subheader("3. Pola: merchant paling banyak berada dekat jenis tempat apa?")

#     @st.cache_data(show_spinner=False)
#     def background_points(p_lat, p_lon, m_lat, m_lon, n=3000, max_d=1000):
#         rng = np.random.default_rng(42)
#         lat = np.concatenate([p_lat, m_lat])
#         lon = np.concatenate([p_lon, m_lon])
#         cl = rng.uniform(lat.min(), lat.max(), n * 5)
#         co = rng.uniform(lon.min(), lon.max(), n * 5)
#         d, _ = BallTree(rad(lat, lon), metric="haversine").query(rad(cl, co), k=1)
#         keep = d[:, 0] * EARTH <= max_d
#         cl, co = cl[keep], co[keep]
#         idx = rng.permutation(len(cl))[:n]
#         return cl[idx], co[idx]

#     @st.cache_data(show_spinner=False)
#     def lift_per_kelompok(p_lat, p_lon, p_grp, m_lat, m_lon, b_lat, b_lon, r, min_n=10):
#         bg_mean = count_within(rad(b_lat, b_lon), rad(m_lat, m_lon), r).mean()
#         if not bg_mean > 0:
#             return pd.DataFrame()
#         cnt = near(p_lat, p_lon, m_lat, m_lon, r, 30)
#         grp = np.array(p_grp)
#         rows = []
#         for gname in np.unique(grp):
#             a = cnt[grp == gname]
#             if len(a) >= min_n:
#                 rows.append({"Jenis tempat": gname, "Jumlah tempat": int(len(a)), "Lift": round(float(a.mean() / bg_mean), 2)})
#         if not rows:
#             return pd.DataFrame()
#         return pd.DataFrame(rows).sort_values("Lift", ascending=False).reset_index(drop=True)

#     if poi is None or len(df) < 30:
#         st.info("Butuh data POI dan minimal 30 merchant untuk melihat pola.")
#     else:
#         b_lat, b_lon = background_points(poi["latitude"].to_numpy(), poi["longitude"].to_numpy(), df["lat"].to_numpy(), df["lon"].to_numpy())
#         pola = lift_per_kelompok(poi["latitude"].to_numpy(), poi["longitude"].to_numpy(), poi["kelompok"].tolist(),
#                                  df["lat"].to_numpy(), df["lon"].to_numpy(), b_lat, b_lon, r_m)
#         if pola.empty:
#             st.info("Pola belum bisa dihitung dengan data ini.")
#         else:
#             atas = pola[pola["Lift"] > 1].head(3)
#             if not atas.empty:
#                 kalimat = ", ".join(a + " (" + format(b, ".1f") + "x)" for a, b in zip(atas["Jenis tempat"], atas["Lift"]))
#                 st.markdown("Merchant paling sering berada dekat: **" + kalimat + "** dibanding titik acak di area yang sama.")
#             st.bar_chart(pola.set_index("Jenis tempat")["Lift"])
#             st.caption(
#                 "Angka 1 = sama dengan titik acak, 2 = dua kali lebih ramai merchant. Ini asosiasi, bukan sebab: "
#                 "sekolah bisa tampak menarik merchant hanya karena berada di permukiman padat, dan sebaran merchant "
#                 "mencerminkan di mana sales pernah bekerja."
#             )

#     with st.expander("Bahan pembanding: biasanya ada berapa merchant di sekitar tiap jenis tempat?"):
#         if ref_table is None or ref_table.empty:
#             st.info("Belum tersedia (butuh data POI dan minimal 30 merchant).")
#         else:
#             st.caption("'Biasanya' adalah angka pembanding untuk menilai apakah suatu titik kekurangan merchant. "
#                        "Kalau angkanya terlihat janggal untuk satu jenis tempat, urutan prioritas jenis itu perlu dicurigai.")
#             st.dataframe(ref_table, hide_index=True)
        
"""
Peta Potensi Merchant - Pulogadung (2 halaman: Peta dan Daftar kunjungan).

    pip install streamlit folium streamlit-folium scikit-learn pandas numpy openpyxl
    streamlit run app_peta_merchant.py

Taruh di folder yang sama:
    merchant_geocoded_filtered.csv   (harus punya kolom latitude & longitude)
    poi_filtered.csv                 (osm_key, nama, kategori, latitude, longitude)
Atau upload lewat sidebar > "Ganti / upload data".
"""

import datetime as dt
import html
import io
import os

import folium
import numpy as np
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from sklearn.neighbors import BallTree
from streamlit_folium import st_folium

st.set_page_config(page_title="Peta Potensi Merchant", page_icon="📍", layout="wide")

# Streamlit baru memakai width="stretch"; versi lama memakai use_container_width=True.
try:
    _v = tuple(int(x) for x in st.__version__.split(".")[:2])
except Exception:
    _v = (0, 0)
STRETCH = {"width": "stretch"} if _v >= (1, 50) else {"use_container_width": True}

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
    div[data-testid="stMetric"] {
        background: rgba(128,128,128,0.10); border: 1px solid rgba(128,128,128,0.28);
        border-radius: 12px; padding: 12px 16px;
    }
    .nomor {display: inline-block; background: #1971c2; color: #fff; border-radius: 50%; width: 26px; height: 26px;
            text-align: center; line-height: 26px; margin-right: 8px; font-weight: 700; font-size: 0.9rem;}
    .kecil {opacity: 0.7; font-size: 0.85rem;}
    .legend span.dot {font-size: 20px; vertical-align: middle;}
    .legend {margin: 2px 0 10px 0; line-height: 2;}
    .badge {display: inline-block; background: #1971c2; color: #fff; border-radius: 50%; width: 20px; height: 20px;
            text-align: center; line-height: 20px; font-size: 11px; font-weight: 700; vertical-align: middle;}
    .gradmini {display: inline-block; width: 80px; height: 10px; border-radius: 5px; vertical-align: middle; margin: 0 6px;
               background: linear-gradient(90deg, #ffffb2, #fd8d3c, #bd0026);}
    </style>
    """,
    unsafe_allow_html=True,
)

MERCHANT_FILES = ["merchant_geocoded_filtered.csv"]
DEFAULT_POI = "poi_filtered.csv"
EARTH = 6371000.0
GEO_OK = ["ok", "fallback_1", "fallback_2"]
DATA_DATE = dt.date(2026, 11, 16)     # tanggal tarikan data; kolom *_ytd dihitung sampai tanggal ini
ZOOM_FOKUS = 17                       # level zoom peta saat titik potensial diklik
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember"]

STATUS_ORDER = ["Aktif", "Menurun", "Tidak aktif"]
STATUS_COLOR = {"Aktif": "#2f9e44", "Menurun": "#f08c00", "Tidak aktif": "#e03131"}

# Jenis tempat yang dianggap "jangkar" (penarik keramaian) beserta namanya dalam bahasa Indonesia.
KAT_ID = {
    "school": "Sekolah", "kindergarten": "TK / PAUD", "college": "Perguruan tinggi", "university": "Universitas",
    "industrial": "Kawasan industri", "factory": "Pabrik", "works": "Pabrik", "warehouse": "Gudang",
    "company": "Perusahaan", "office": "Kantor", "commercial": "Area komersial", "marketplace": "Pasar",
    "mall": "Mal", "supermarket": "Supermarket", "department_store": "Toserba", "retail": "Area ritel",
    "hospital": "Rumah sakit", "clinic": "Klinik", "bus_station": "Terminal / halte", "government": "Kantor pemerintah",
    "community_centre": "Balai warga", "stadium": "Stadion", "sports_centre": "Pusat olahraga", "hotel": "Hotel",
    "apartment": "Apartemen",
}

NOISE = {
    "parking", "parking_entrance", "parking_space", "motorcycle_parking", "track", "toilets", "fountain",
    "water", "ticket_validator", "bicycle_repair_station", "grave_yard", "garden", "playground",
    "horse_riding", "artwork", "outdoor", "alternative", "oil", "it", "social_facility",
}
GROUPS = {
    "Pendidikan": ["school", "kindergarten", "prep_school", "college", "university", "educational_institution", "language_school", "library"],
    "Tempat ibadah": ["place_of_worship"],
    "Pemerintahan": ["government", "police", "fire_station", "military", "administrative", "post_office", "political_party", "community_centre"],
    "Kesehatan": ["hospital", "clinic", "pharmacy", "doctors", "dentist", "midwife", "chemist", "medical_supply", "veterinary"],
    "Industri & gudang": ["industrial", "factory", "warehouse", "works", "logistics", "depot", "storage_rental"],
    "Kantor & komersial": ["company", "office", "commercial", "estate_agent", "insurance_agent"],
    "Pasar & retail": ["marketplace", "mall", "supermarket", "department_store", "retail", "convenience", "general", "variety_store",
                       "hardware", "doityourself", "kiosk", "greengrocer", "grocery", "clothes", "shoes", "electronics",
                       "mobile_phone", "copyshop", "stationery"],
    "Kuliner": ["restaurant", "fast_food", "cafe", "coffee", "food_court", "ice_cream", "pub", "bar", "bakery", "pastry",
                "chocolate", "beverages", "frozen", "alcohol"],
    "Transportasi & otomotif": ["bus_station", "fuel", "charging_station", "car_repair", "car_wash", "car_parts", "car", "motorcycle", "bicycle"],
    "Bank & keuangan": ["bank", "atm", "bureau_de_change"],
    "Olahraga & rekreasi": ["park", "sports_centre", "sports", "pitch", "stadium", "swimming_pool", "fitness_centre", "golf_course",
                            "cinema", "amusement_arcade", "nightclub"],
    "Penginapan": ["hotel", "guest_house", "apartment"],
}
CAT2GROUP = {c: g for g, cats in GROUPS.items() for c in cats}


# ---------------- Fungsi bantu ----------------
def esc(x):
    return html.escape(str(x))


def idn(x, dec=0):
    """Angka format Indonesia: titik untuk ribuan, koma untuk desimal (1.180 / 11,9)."""
    s = format(float(x), ",." + str(dec) + "f")
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def ringkas(x):
    """Rupiah ringkas: M = miliar, Jt = juta."""
    x = float(x)
    if abs(x) >= 1e9:
        return idn(x / 1e9, 1) + " M"
    if abs(x) >= 1e6:
        return idn(x / 1e6, 1) + " Jt"
    return idn(x)


def tgl_indo(d):
    return str(d.day) + " " + BULAN[d.month - 1] + " " + str(d.year)


def guess(columns, candidates):
    lower = {c.lower().strip(): c for c in columns}
    for name in candidates:
        if name in lower:
            return lower[name]
    return None


def read_file(f):
    if f.name.lower().endswith(".csv"):
        return pd.read_csv(f)
    return pd.read_excel(f)


def rad(lat, lon):
    return np.radians(np.column_stack([np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)]))


def count_within(q, t, r_m):
    if len(t) == 0:
        return np.zeros(len(q), dtype=int)
    return BallTree(t, metric="haversine").query_radius(q, r=r_m / EARTH, count_only=True)


def near(p_lat, p_lon, m_lat, m_lon, r_m, excl_m):
    """Jumlah merchant dalam r_m dari tiap POI. Merchant dalam excl_m meter (kemungkinan usaha yang sama dengan POI) tidak dihitung."""
    q, t = rad(p_lat, p_lon), rad(m_lat, m_lon)
    c = count_within(q, t, r_m)
    if excl_m > 0:
        c = c - count_within(q, t, excl_m)
    return np.clip(c, 0, None)


def gmaps(lat, lon):
    return "https://www.google.com/maps?q=" + str(lat) + "," + str(lon)


def pilih_tersebar(cand, n, min_sep_m):
    """Ambil n kandidat teratas yang saling berjauhan (min_sep_m) dan bervariasi: jumlah titik dari satu kelompok
    jenis tempat dibatasi, supaya daftar tidak didominasi satu jenis saja (mis. rumah sakit atau mal)."""
    if cand.empty:
        return cand
    lat = np.radians(cand["latitude"].to_numpy())
    lon = np.radians(cand["longitude"].to_numpy())
    grp = cand["kelompok"].to_numpy()
    jns = cand["jenis"].to_numpy()
    cap_jenis = max(2, int(np.ceil(n / 4)))      # batas per jenis tempat (mis. Sekolah)
    cap_grup = max(cap_jenis, int(np.ceil(n / 2)))   # batas per kelompok (mis. Pendidikan = Sekolah + TK + kampus)

    def jauh_dari_terpilih(i, chosen):
        if not chosen:
            return True
        c = np.array(chosen)
        a = np.sin((lat[c] - lat[i]) / 2) ** 2 + np.cos(lat[i]) * np.cos(lat[c]) * np.sin((lon[c] - lon[i]) / 2) ** 2
        return not (2 * EARTH * np.arcsin(np.sqrt(a)) < min_sep_m).any()

    chosen, count, count_j = [], {}, {}
    for batas in (True, False):    # putaran 1: dengan batas per jenis dan kelompok; putaran 2: isi sisa tanpa batas
        for i in range(len(cand)):
            if len(chosen) >= n:
                break
            if i in chosen or (batas and (count.get(grp[i], 0) >= cap_grup or count_j.get(jns[i], 0) >= cap_jenis)):
                continue
            if jauh_dari_terpilih(i, chosen):
                chosen.append(i)
                count[grp[i]] = count.get(grp[i], 0) + 1
                count_j[jns[i]] = count_j.get(jns[i], 0) + 1
    chosen.sort()                  # pertahankan urutan prioritas
    return cand.iloc[chosen]


def set_fokus(lat, lon):
    st.session_state["fokus"] = (float(lat), float(lon))


def reset_fokus():
    st.session_state["fokus"] = None


# ---------------- Sidebar ----------------
st.sidebar.title("📍 Peta Potensi Merchant")
with st.sidebar.expander("Ganti / upload data"):
    mfile = st.file_uploader("Data merchant (CSV / Excel)", type=["csv", "xlsx", "xls"])
    pfile = st.file_uploader("Data tempat ramai dari OpenStreetMap (CSV)", type=["csv"])
    rfile = st.file_uploader("Hasil model building_potensi.csv (opsional)", type=["csv"])

raw, src = None, None
try:
    if mfile is not None:
        raw, src = read_file(mfile), mfile.name
    else:
        for fn in MERCHANT_FILES:
            if os.path.exists(fn):
                raw, src = pd.read_csv(fn), fn
                break
except Exception as e:
    st.sidebar.error("File merchant tidak bisa dibaca: " + str(e))

if raw is None:
    st.title("Peta Potensi Merchant")
    st.info("Data merchant belum ditemukan. Taruh `" + MERCHANT_FILES[0] + "` di folder yang sama dengan aplikasi ini, "
            "atau upload lewat sidebar > Ganti / upload data.")
    st.stop()
cols = list(raw.columns)

poi_raw = None
try:
    if pfile is not None:
        poi_raw = pd.read_csv(pfile)
    elif os.path.exists(DEFAULT_POI):
        poi_raw = pd.read_csv(DEFAULT_POI)
except Exception as e:
    st.sidebar.error("File tempat ramai tidak bisa dibaca: " + str(e))

lat_col = guess(cols, ["latitude", "lat", "lintang", "geo_lat"])
lon_col = guess(cols, ["longitude", "lon", "lng", "long", "bujur", "geo_lon"])
if not lat_col or not lon_col:
    st.title("Peta Potensi Merchant")
    st.error("Data merchant belum punya kolom koordinat (latitude dan longitude), jadi belum bisa dipetakan.")
    st.markdown(
        "Kolom yang terbaca: `" + "`, `".join(cols[:25]) + "`" + (" ..." if len(cols) > 25 else "") + "\n\n"
        "**Langkah:** lakukan geocoding kolom `address` dulu, simpan hasilnya sebagai CSV yang memuat kolom `latitude` dan "
        "`longitude` (serta `geocode_status` bila ada), lalu taruh di folder ini atau upload di sidebar."
    )
    st.stop()

geo_col = guess(cols, ["geocode_status"])
id_col = guess(cols, ["store_id", "merchant_id", "mid", "id"])
nama_col = guess(cols, ["store_name", "nama_merchant", "nama", "name"])
kat_col = guess(cols, ["lob_lm", "kategori", "category", "jenis_usaha"])
cab_col = guess(cols, ["nama_cabang_final", "cabang", "branch"])
f30_col = guess(cols, ["freq_30_days", "frek_30", "trx_30"])
s30_col = guess(cols, ["sv_30_days", "sales_30", "nominal_30"])
fytd_col = guess(cols, ["freq_ytd", "frek_ytd", "trx_ytd"])
sytd_col = guess(cols, ["sv_ytd", "sales_ytd", "nominal_ytd"])

with st.sidebar.expander("Pengaturan (opsional)"):
    st.caption("Sudah terisi nilai yang disarankan. Biasanya tidak perlu diubah.")
    data_date = st.date_input("Tanggal tarikan data", DATA_DATE, help="Data tahun berjalan (YTD) dihitung sampai tanggal ini.")
    months = max(1.0, ((data_date - dt.date(data_date.year, 1, 1)).days + 1) / (365.25 / 12))
    min_active = st.number_input("Merchant disebut Aktif jika transaksi 30 hari minimal", 1, 1000, 20)
    min_sales = st.number_input("... dan sales 30 hari lebih dari (Rp)", 0, 10**12, 100000, 10000)
    drop_pct = st.slider("Dianggap menurun jika transaksi turun lebih dari (%)", 10, 90, 50,
                         help="Dibandingkan rata-rata transaksi per bulan sejak awal tahun.")
    r_m = st.slider("Area sekitar tempat ramai yang dihitung (meter)", 100, 500, 300, 50,
                    help="Merchant yang berada dalam jarak ini dari suatu sekolah/pasar/pabrik dihitung sebagai 'merchant di sekitarnya'.")
    min_sep = st.slider("Jarak minimal antar titik potensial (meter)", 100, 1000, 300, 50,
                        help="Supaya titik yang disarankan tidak menumpuk di satu tempat.")
    min_eks = st.number_input("Abaikan tempat yang biasanya hanya punya merchant kurang dari", 0.0, 50.0, 1.0, 0.5,
                              help="Tempat yang biasanya memang sepi merchant tidak dianggap peluang.")
    only_geo_ok = st.checkbox("Hanya pakai alamat yang titiknya akurat", value=True, disabled=geo_col is None)

if not geo_col:
    only_geo_ok = False


# ---------------- Susun data merchant ----------------
def num(c):
    if c:
        return pd.to_numeric(raw[c], errors="coerce").fillna(0)
    return pd.Series(0.0, index=raw.index)


def text(c, default):
    if c:
        return raw[c].fillna("-").astype(str)
    return pd.Series(default, index=raw.index)


f30, fytd = num(f30_col), num(fytd_col)
avg_month = fytd / months
sharp = (avg_month > 0) & (f30 < avg_month * (1 - drop_pct / 100))
s30 = num(s30_col)
low_sales = (s30 <= min_sales) if s30_col else False
low = (f30 > 0) & ((f30 < min_active) | low_sales)      # ada transaksi, tapi belum memenuhi ambang Aktif
status = np.select([f30 <= 0, sharp | low], [STATUS_ORDER[2], STATUS_ORDER[1]], default=STATUS_ORDER[0])

df = pd.DataFrame(
    {
        "id": raw[id_col].astype(str) if id_col else raw.index.astype(str),
        "nama": text(nama_col, "(tanpa nama)"),
        "kategori": text(kat_col, "-"),
        "cabang": text(cab_col, "-"),
        "geocode": text(geo_col, "-"),
        "lat": pd.to_numeric(raw[lat_col], errors="coerce"),
        "lon": pd.to_numeric(raw[lon_col], errors="coerce"),
        "frek_30": f30,
        "sv_30": s30,
        "frek_ytd": fytd,
        "sv_ytd": num(sytd_col),
        "status": status,
    }
)
n_raw = len(df)
df = df.dropna(subset=["lat", "lon"])
df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]
if only_geo_ok:
    df = df[df["geocode"].isin(GEO_OK)]
if df.empty:
    st.error("Tidak ada titik koordinat yang layak untuk dipetakan.")
    st.stop()
st.sidebar.caption("Merchant: " + str(src) + " | dipetakan " + idn(len(df)) + " dari " + idn(n_raw) + " baris")

# ---------------- Siapkan tempat ramai (POI) ----------------
poi = None
if poi_raw is not None:
    if {"latitude", "longitude", "kategori"}.issubset(set(poi_raw.columns)):
        poi = poi_raw.copy()
        poi["latitude"] = pd.to_numeric(poi["latitude"], errors="coerce")
        poi["longitude"] = pd.to_numeric(poi["longitude"], errors="coerce")
        poi = poi.dropna(subset=["latitude", "longitude", "kategori"])
        poi = poi[~poi["kategori"].isin(NOISE)].reset_index(drop=True)
        if "nama" not in poi.columns:
            poi["nama"] = ""
        poi["nama"] = poi["nama"].fillna("").astype(str)
        if "osm_key" not in poi.columns:
            poi["osm_key"] = "idx/" + poi.index.astype(str)
        poi["kelompok"] = poi["kategori"].map(CAT2GROUP).fillna("Lainnya")
        if poi.empty:
            poi = None
    else:
        st.sidebar.error("File tempat ramai harus punya kolom: latitude, longitude, kategori.")

# ---------------- Hitung kandidat titik potensial ----------------
cand = pd.DataFrame()
ref_table = None
alasan_kosong = ""
if poi is None:
    alasan_kosong = "Data tempat ramai (poi_filtered.csv) belum tersedia."
elif len(df) < 30:
    alasan_kosong = "Merchant yang dipetakan kurang dari 30, terlalu sedikit untuk membandingkan."
else:
    base = poi.copy()
    base["merchant_sekitar"] = near(base["latitude"].to_numpy(), base["longitude"].to_numpy(),
                                    df["lat"].to_numpy(), df["lon"].to_numpy(), r_m, 30)
    mu_all = float(base["merchant_sekitar"].mean())
    g = base.groupby("kategori")["merchant_sekitar"].agg(["sum", "count"])
    mu = (g["sum"] + 10 * mu_all) / (g["count"] + 10)       # rata-rata sekategori, disusutkan ke rata-rata umum
    base["biasanya"] = base["kategori"].map(mu)
    if rfile is not None:
        try:
            res = pd.read_csv(rfile)
            if {"osm_key", "ekspektasi"}.issubset(set(res.columns)):
                base = base.merge(res[["osm_key", "ekspektasi"]], on="osm_key", how="left")
                base["biasanya"] = base["ekspektasi"].fillna(base["biasanya"])
            else:
                st.sidebar.warning("File hasil model harus punya kolom osm_key dan ekspektasi.")
        except Exception as e:
            st.sidebar.warning("File hasil model tidak bisa dibaca: " + str(e))
    base["selisih"] = base["biasanya"] - base["merchant_sekitar"]
    base["skor"] = base["selisih"] / np.sqrt(base["biasanya"].clip(lower=1))   # selisih relatif terhadap skala jenis tempatnya
    base["jenis"] = base["kategori"].map(KAT_ID)
    # Peringkat di dalam jenisnya sendiri: 0.99 = termasuk 1% paling kekurangan merchant dibanding tempat sejenis.
    # (rank - 0.5) / jumlah: jenis yang tempatnya sedikit tidak otomatis menempati puncak.
    grp_rank = base.groupby("kategori")["skor"].rank(method="average")
    base["peringkat"] = (grp_rank - 0.5) / base.groupby("kategori")["skor"].transform("count")
    ref_table = (
        base[base["jenis"].notna()].groupby("jenis")
        .agg(**{"Jumlah tempat": ("kategori", "size"), "Rata-rata merchant sekitar": ("merchant_sekitar", "mean"),
                "Biasanya": ("biasanya", "mean")})
        .round(1).sort_values("Jumlah tempat", ascending=False).reset_index().rename(columns={"jenis": "Jenis tempat"})
    )
    cand = base[base["jenis"].notna() & (base["selisih"] > 0) & (base["biasanya"] >= min_eks)]
    cand = cand.sort_values(["peringkat", "skor", "selisih"], ascending=False)
    if cand.empty:
        alasan_kosong = "Tidak ada tempat yang merchant-nya jauh di bawah kebiasaan tempat serupa dengan pengaturan sekarang."

# ---------------- Judul & ringkasan ----------------
st.title("Peta Potensi Merchant - Pulogadung")
st.caption("Data per " + tgl_indo(data_date) + "  |  " + idn(len(df)) + " merchant dipetakan")

total = len(df)
n_aktif = int((df["status"] == "Aktif").sum())
sales_30 = float(df["sv_30"].sum())
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total merchant", idn(total))
k2.metric("Aktif", idn(n_aktif), idn(n_aktif / total * 100) + "% dari total", delta_color="off")
k3.metric("Perlu ditindaklanjuti", idn(total - n_aktif), "menurun atau tidak aktif", delta_color="off")
k4.metric("Sales 30 hari", ringkas(sales_30), idn(sales_30), delta_color="off", help="M = miliar rupiah, Jt = juta rupiah")

tab_peta, tab_daftar = st.tabs(["🗺️ Peta", "📋 Daftar kunjungan"])

# ============================ HALAMAN 1: PETA ============================
with tab_peta:
    c1, c2, c3, c4 = st.columns([1, 1.3, 1.6, 2])
    show_m = c1.checkbox("Merchant", value=True, help="Titik hijau/oranye/merah = merchant yang sudah ada.")
    show_p = c2.checkbox("Titik potensial", value=True, disabled=cand.empty,
                         help="Angka biru = tempat ramai yang merchant di sekitarnya masih sedikit. Nomor 1 = prioritas utama.")
    show_h = c3.checkbox("Kepadatan merchant", value=True,
                         help="Warna hangat = banyak merchant yang SUDAH ada. Ini bukan petunjuk potensi.")
    n_pot = c4.slider("Jumlah titik potensial", 5, 30, 10)

    with st.expander("Filter tampilan (status merchant, jenis tempat)"):
        f1, f2 = st.columns(2)
        pilih_status = f1.multiselect("Tampilkan merchant berstatus", STATUS_ORDER, default=STATUS_ORDER)
        jenis_opsi = sorted(cand["jenis"].unique()) if not cand.empty else []
        pilih_jenis = f2.multiselect("Cari titik potensial di jenis tempat", jenis_opsi, default=jenis_opsi, disabled=cand.empty,
                                     help="Hapus yang tidak diinginkan, misalnya hanya sisakan Sekolah dan Pasar.")

    cand_f = cand[cand["jenis"].isin(pilih_jenis)] if not cand.empty else cand
    sel = pilih_tersebar(cand_f, n_pot, min_sep) if not cand_f.empty else cand_f
    pesan_kosong = alasan_kosong
    if not cand.empty and cand_f.empty:
        pesan_kosong = "Belum ada jenis tempat yang dipilih."

    legend = " &nbsp;&nbsp; ".join(
        "<span class='dot' style='color:" + STATUS_COLOR[s] + "'>&#9679;</span> " + s for s in STATUS_ORDER
    )
    legend += " &nbsp;&nbsp; <span class='badge'>1</span> Titik potensial (urut prioritas)"
    if show_h:
        legend += " &nbsp;&nbsp; Kepadatan: sedikit <span class='gradmini'></span> banyak"
    st.markdown("<div class='legend'>" + legend + "</div>", unsafe_allow_html=True)

    left, right = st.columns([3, 1.35])

    with left:
        fokus = st.session_state.get("fokus")
        center = [df["lat"].mean(), df["lon"].mean()]
        m = folium.Map(location=list(fokus) if fokus else center, zoom_start=ZOOM_FOKUS if fokus else 14,
                       tiles="OpenStreetMap", control_scale=True)

        if show_h:
            HeatMap(df[["lat", "lon"]].values.tolist(), radius=25, blur=20, min_opacity=0.3,
                    gradient={0.2: "#ffffb2", 0.5: "#fd8d3c", 1.0: "#bd0026"}).add_to(m)

        if show_m:
            for r in df[df["status"].isin(pilih_status)].itertuples():
                color = STATUS_COLOR[r.status]
                popup = (
                    "<b>" + esc(r.nama) + "</b><br>" + esc(r.kategori) + "<br>Status: <b>" + r.status + "</b>"
                    + "<br>Transaksi 30 hari: " + idn(r.frek_30)
                    + "<br>Sales 30 hari: " + idn(r.sv_30)
                    + "<br><a href='" + gmaps(r.lat, r.lon) + "' target='_blank'>Buka di Google Maps</a>"
                )
                folium.CircleMarker(
                    location=[r.lat, r.lon], radius=5, color="#ffffff", weight=1, fill=True, fill_color=color,
                    fill_opacity=0.9, tooltip=esc(r.nama) + " - " + r.status, popup=folium.Popup(popup, max_width=280),
                ).add_to(m)

        if show_p and not sel.empty:
            for rank, r in enumerate(sel.itertuples(), 1):
                judul = r.nama if r.nama.strip() else r.jenis + " (tanpa nama)"
                popup = (
                    "<b>#" + str(rank) + " " + esc(judul) + "</b><br>" + esc(r.jenis)
                    + "<br>Merchant dalam " + str(r_m) + " m: <b>" + idn(r.merchant_sekitar) + "</b>"
                    + "<br>Tempat serupa biasanya: <b>" + idn(r.biasanya) + "</b>"
                    + "<br><a href='" + gmaps(r.latitude, r.longitude) + "' target='_blank'>Buka di Google Maps</a>"
                )
                folium.Circle(
                    location=[r.latitude, r.longitude], radius=r_m, color="#1971c2", weight=2, dash_array="6",
                    fill=True, fill_color="#1971c2", fill_opacity=0.10,
                ).add_to(m)
                badge = (
                    "<div style='background:#1971c2;color:#fff;border:2px solid #fff;border-radius:50%;width:30px;height:30px;"
                    "line-height:26px;text-align:center;font-weight:700;font-size:14px;box-shadow:0 1px 5px rgba(0,0,0,.55)'>"
                    + str(rank) + "</div>"
                )
                folium.Marker(
                    location=[r.latitude, r.longitude],
                    icon=folium.DivIcon(html=badge, icon_size=(30, 30), icon_anchor=(15, 15)),
                    tooltip="#" + str(rank) + " " + esc(judul), popup=folium.Popup(popup, max_width=300),
                ).add_to(m)

        pts_lat = list(df["lat"]) + (list(sel["latitude"]) if show_p and not sel.empty else [])
        pts_lon = list(df["lon"]) + (list(sel["longitude"]) if show_p and not sel.empty else [])
        if fokus:
            st_folium(m, width=None, height=650, returned_objects=[], center=list(fokus), zoom=ZOOM_FOKUS)
        else:
            m.fit_bounds([[min(pts_lat), min(pts_lon)], [max(pts_lat), max(pts_lon)]])
            st_folium(m, width=None, height=650, returned_objects=[])

    with right:
        st.subheader("Titik potensial")
        if sel.empty:
            st.info(pesan_kosong or "Belum ada titik potensial.")
        else:
            if st.session_state.get("fokus"):
                st.button("↩ Kembali ke peta penuh", on_click=reset_fokus, **STRETCH)
            else:
                st.caption("Klik 🔍 untuk memperbesar peta ke titik itu.")
            with st.container(height=600):
                for rank, r in enumerate(sel.itertuples(), 1):
                    judul = r.nama if r.nama.strip() else r.jenis + " (tanpa nama)"
                    sedang = st.session_state.get("fokus") == (float(r.latitude), float(r.longitude))
                    with st.container(border=True):
                        teks, tombol = st.columns([5, 1], vertical_alignment="center")
                        teks.markdown(
                            "<span class='nomor'>" + str(rank) + "</span><b>" + esc(judul) + "</b>"
                            + (" <span class='kecil'>(sedang dilihat)</span>" if sedang else "") + "<br>"
                            "<span class='kecil'>" + esc(r.jenis) + "</span><br>"
                            "<a href='" + gmaps(r.latitude, r.longitude) + "' target='_blank'>Buka di Google Maps</a>",
                            unsafe_allow_html=True,
                        )
                        tombol.button("🔍", key="fokus_" + str(rank), on_click=set_fokus,
                                      args=(r.latitude, r.longitude), help="Lihat")

    with st.expander("Cara membaca peta"):
        st.markdown(
            "- **Titik berwarna** adalah merchant. Hijau = aktif (minimal " + str(min_active) + " transaksi dan sales lebih dari Rp"
            + idn(min_sales) + " dalam 30 hari), oranye = menurun, merah = tidak ada transaksi dalam 30 hari.\n"
            "- **Warna merah-kuning di peta** menunjukkan di mana merchant yang sudah ada paling banyak. Ini bukan tempat potensial.\n"
            "- **Angka biru** adalah titik potensial: sekolah, pasar, pabrik, mal, dll yang merchant di sekitarnya (radius "
            + str(r_m) + " m) jauh lebih sedikit daripada tempat sejenis lainnya. Nomor 1 = prioritas utama.\n"
            "- Ini petunjuk untuk dicek di lapangan, **bukan jaminan** kunjungan akan menambah merchant. Area kosong atau yang "
            "sudah dijangkau cabang lain tidak terdeteksi otomatis."
        )

# ============================ HALAMAN 2: DAFTAR ============================
with tab_daftar:
    st.subheader("1. Titik potensial untuk dikunjungi")
    if sel.empty:
        st.info(pesan_kosong or "Belum ada titik potensial.")
    else:
        t1 = sel.copy().reset_index(drop=True)
        t1.insert(0, "Prioritas", range(1, len(t1) + 1))
        t1["Nama"] = [(n if n.strip() else j + " (tanpa nama)") for n, j in zip(t1["nama"], t1["jenis"])]
        t1["Alasan"] = ["Baru " + idn(a) + " merchant dalam " + str(r_m) + " m, biasanya sekitar " + idn(b)
                        for a, b in zip(t1["merchant_sekitar"], t1["biasanya"])]
        t1["Peta"] = [gmaps(a, b) for a, b in zip(t1["latitude"], t1["longitude"])]
        show1 = t1[["Prioritas", "Nama", "jenis", "merchant_sekitar", "biasanya", "Alasan", "Peta"]].rename(
            columns={"jenis": "Jenis tempat", "merchant_sekitar": "Merchant di sekitar", "biasanya": "Biasanya"})
        show1["Biasanya"] = show1["Biasanya"].round(0)
        st.dataframe(show1, hide_index=True, **STRETCH,
                     column_config={"Peta": st.column_config.LinkColumn("Peta", display_text="Buka")})
        out = io.StringIO()
        show1.to_csv(out, index=False)
        st.download_button("⬇ Unduh daftar titik potensial (CSV)", out.getvalue(), "titik_potensial.csv", "text/csv")

    st.subheader("2. Merchant yang perlu ditindaklanjuti")
    st.caption("Diurutkan dari sales YTD terbesar: merchant yang dulu bernilai besar dan sekarang turun atau berhenti ada di atas.")
    t2 = df[df["status"] != "Aktif"].copy()
    if t2.empty:
        st.success("Semua merchant berstatus aktif.")
    else:
        cf1, cf2 = st.columns([1.2, 2])
        f_status = cf1.radio("Tampilkan", ["Semua", "Menurun", "Tidak aktif"], horizontal=True)
        cari = cf2.text_input("Cari nama merchant", placeholder="ketik sebagian nama...")
        if f_status != "Semua":
            t2 = t2[t2["status"] == f_status]
        if cari.strip():
            t2 = t2[t2["nama"].str.contains(cari.strip(), case=False, regex=False)]
        if t2.empty:
            st.info("Tidak ada merchant yang cocok dengan pilihan ini.")
        else:
            t2["Tindakan"] = np.where(
                t2["status"] == "Menurun", "Kunjungi, tanyakan kendala transaksi",
                np.where(t2["frek_ytd"] <= 0, "Aktivasi: bantu transaksi pertama", "Hubungi, pastikan usaha masih beroperasi"),
            )
            t2["Peta"] = [gmaps(a, b) for a, b in zip(t2["lat"], t2["lon"])]
            t2 = t2.sort_values("sv_ytd", ascending=False)
            show2 = t2[["nama", "kategori", "cabang", "status", "frek_30", "sv_ytd", "Tindakan", "Peta"]].rename(
                columns={"nama": "Nama", "kategori": "Kategori usaha", "cabang": "Cabang", "status": "Status",
                         "frek_30": "Trx 30 hari", "sv_ytd": "Sales YTD"})
            st.caption("Menampilkan " + idn(min(len(show2), 200)) + " dari " + idn(len(show2)) + " merchant.")
            st.dataframe(show2.head(200), hide_index=True, **STRETCH,
                         column_config={"Peta": st.column_config.LinkColumn("Peta", display_text="Buka"),
                                        "Sales YTD": st.column_config.NumberColumn("Sales YTD", format="%d"),
                                        "Trx 30 hari": st.column_config.NumberColumn("Trx 30 hari", format="%d")})
            out = io.StringIO()
            show2.to_csv(out, index=False)
            st.download_button("⬇ Unduh daftar merchant (CSV)", out.getvalue(), "merchant_tindak_lanjut.csv", "text/csv")

    st.subheader("3. Pola: merchant paling banyak berada dekat jenis tempat apa?")

    @st.cache_data(show_spinner=False)
    def background_points(p_lat, p_lon, m_lat, m_lon, n=3000, max_d=1000):
        rng = np.random.default_rng(42)
        lat = np.concatenate([p_lat, m_lat])
        lon = np.concatenate([p_lon, m_lon])
        cl = rng.uniform(lat.min(), lat.max(), n * 5)
        co = rng.uniform(lon.min(), lon.max(), n * 5)
        d, _ = BallTree(rad(lat, lon), metric="haversine").query(rad(cl, co), k=1)
        keep = d[:, 0] * EARTH <= max_d
        cl, co = cl[keep], co[keep]
        idx = rng.permutation(len(cl))[:n]
        return cl[idx], co[idx]

    @st.cache_data(show_spinner=False)
    def lift_per_kelompok(p_lat, p_lon, p_grp, m_lat, m_lon, b_lat, b_lon, r, min_n=10):
        bg_mean = count_within(rad(b_lat, b_lon), rad(m_lat, m_lon), r).mean()
        if not bg_mean > 0:
            return pd.DataFrame()
        cnt = near(p_lat, p_lon, m_lat, m_lon, r, 30)
        grp = np.array(p_grp)
        rows = []
        for gname in np.unique(grp):
            a = cnt[grp == gname]
            if len(a) >= min_n:
                rows.append({"Jenis tempat": gname, "Jumlah tempat": int(len(a)), "Lift": round(float(a.mean() / bg_mean), 2)})
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("Lift", ascending=False).reset_index(drop=True)

    if poi is None or len(df) < 30:
        st.info("Butuh data tempat ramai dan minimal 30 merchant untuk melihat pola.")
    else:
        b_lat, b_lon = background_points(poi["latitude"].to_numpy(), poi["longitude"].to_numpy(), df["lat"].to_numpy(), df["lon"].to_numpy())
        pola = lift_per_kelompok(poi["latitude"].to_numpy(), poi["longitude"].to_numpy(), poi["kelompok"].tolist(),
                                 df["lat"].to_numpy(), df["lon"].to_numpy(), b_lat, b_lon, r_m)
        if pola.empty:
            st.info("Pola belum bisa dihitung dengan data ini.")
        else:
            atas = pola[pola["Lift"] > 1].head(3)
            if not atas.empty:
                kalimat = ", ".join(a + " (" + idn(b, 1) + "x)" for a, b in zip(atas["Jenis tempat"], atas["Lift"]))
                st.markdown("Merchant paling sering berada dekat: **" + kalimat + "** dibanding titik acak di area yang sama.")
            st.bar_chart(pola.set_index("Jenis tempat")[["Lift"]].rename(columns={"Lift": "Kali lebih ramai dari titik acak"}))
            st.caption(
                # "Angka 1 = sama dengan titik acak, 2 = dua kali lebih ramai merchant. Ini hubungan, bukan sebab-akibat: "
                # "sekolah bisa tampak menarik merchant hanya karena berada di permukiman padat."
            )

    # with st.expander("Bahan pembanding: biasanya ada berapa merchant di sekitar tiap jenis tempat?"):
    #     if ref_table is None or ref_table.empty:
    #         st.info("Belum tersedia (butuh data tempat ramai dan minimal 30 merchant).")
    #     else:
    #         st.caption("'Biasanya' adalah angka pembanding untuk menilai apakah suatu titik kekurangan merchant. "
    #                    "Kalau angkanya terlihat janggal untuk satu jenis tempat, urutan prioritas jenis itu perlu dicurigai.")
    #         st.dataframe(ref_table, hide_index=True)
