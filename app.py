import streamlit as st
import pandas as pd
from supabase import create_client
import datetime

# 1. Configuración de Conexión
url = "https://lyhgolnqqguinqpqdybe.supabase.co"
key = "sb_secret_Ffqpjxk5nZxSfEEyv6qcog_G4C3Iapc"
supabase = create_client(url, key)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CEDIS Perote - Control de Materiales", layout="wide", page_icon="🏗️")

# --- SISTEMA DE SESIÓN (LOGIN) ---
if 'rol' not in st.session_state:
    st.session_state.rol = None
    st.session_state.nombre_usuario = None
    st.session_state.usuario_id = None

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

def login():
    with st.sidebar:
        st.title("🔐 Acceso CEDIS Perote")
        email_input = st.text_input("Correo Electrónico")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            try:
                response = supabase.table("usuarios").select("*").eq("email", email_input).eq("password", pass_input).execute()
                if len(response.data) > 0:
                    user_data = response.data[0]
                    st.session_state.rol = user_data['rol']
                    st.session_state.nombre_usuario = user_data['nombre_usuario']
                    st.session_state.usuario_id = user_data['id']
                    st.success(f"Bienvenido a CEDIS Perote, {user_data['nombre_usuario']}")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
                
def subir_archivo(archivo, bucket, folder):
    if archivo is not None:
        try:
            nombre_archivo = f"{folder}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            supabase.storage.from_(bucket).upload(nombre_archivo, archivo.getvalue(), {"content-type": archivo.type})
            return supabase.storage.from_(bucket).get_public_url(nombre_archivo)
        except: return None
    return None

if st.session_state.rol is None:
    login()
    st.info("Por favor, inicia sesión con tus credenciales de CEDIS Perote para continuar.")
else:
    rol, nombre = st.session_state.rol, st.session_state.nombre_usuario
    opciones = ["Inventario", "Nueva Venta", "Registrar Abono", "Clientes","Flota y Unidades","Logística y Envíos","Gestión de Gastos"]
    if rol in ["admin", "dev"]: opciones += ["Registro de Clientes", "Reportes","Inicio"]
    menu = st.sidebar.selectbox("Menú Principal", opciones)
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- PÁGINA: INICIO ---
# --- PÁGINA: INICIO (DASHBOARD) ---
    if menu == "Inicio":
        st.title(f"🏗️ CEDIS Perote - Dashboard")
        
        # 1. Obtención de datos
        res_v = supabase.table("ventas").select("fecha_venta, monto_total, monto_credito, Clientes(nombre)").order("fecha_venta", desc=True).execute()
        res_i = supabase.table("inventario").select("nombre_producto, stock_actual").order("stock_actual").execute()
        
        df_v = pd.DataFrame(res_v.data)
        df_i = pd.DataFrame(res_i.data)

        # 2. Cálculos de Métricas
        t_bruto = df_v['monto_total'].sum() if not df_v.empty else 0
        t_cred = df_v['monto_credito'].sum() if not df_v.empty else 0
        num_ventas = len(df_v) if not df_v.empty else 0
        t_stock_unidades = df_i['stock_actual'].sum() if not df_i.empty else 0

        # 3. Fila de Métricas Principales
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Venta Bruta Total", f"${t_bruto:,.2f}")
        m2.metric("Cartera por Cobrar", f"${t_cred:,.2f}", delta_color="inverse")
        m3.metric("Cant. de Ventas", f"{num_ventas}")
        m4.metric("Inventario Total", f"{t_stock_unidades} und")

        st.divider()

        # 4. Tablas Detalladas
        col_izq, col_der = st.columns(2)

        with col_izq:
            st.subheader("🕒 Últimas 5 Ventas")
            if not df_v.empty:
                # Extraemos el nombre del cliente del objeto JSON de la relación
                df_ultimas = df_v.head(5).copy()
                df_ultimas['Cliente'] = df_ultimas['Clientes'].apply(lambda x: x['nombre'] if x else "N/A")
                df_ultimas['Fecha'] = pd.to_datetime(df_ultimas['fecha_venta']).dt.strftime('%d/%m/%Y %H:%M')
                st.table(df_ultimas[['Fecha', 'Cliente', 'monto_total']])
            else:
                st.info("No hay ventas registradas.")

            st.subheader("⚠️ Top 5 Deudores")
            if not df_v.empty:
                # Agrupamos por cliente para ver quién debe más en total
                df_deudores = df_v.copy()
                df_deudores['Cliente'] = df_deudores['Clientes'].apply(lambda x: x['nombre'] if x else "N/A")
                top_deudores = df_deudores.groupby('Cliente')['monto_credito'].sum().reset_index()
                top_deudores = top_deudores[top_deudores['monto_credito'] > 0].sort_values('monto_credito', ascending=False).head(5)
                
                if not top_deudores.empty:
                    st.dataframe(top_deudores, use_container_width=True, hide_index=True)
                else:
                    st.success("¡No hay deudas pendientes!")
            else:
                st.write("Sin datos de clientes.")

        with col_der:
            st.subheader("📦 Disponibilidad de Inventario")
            if not df_i.empty:
                # Mostramos el inventario, resaltando en rojo si hay poco stock (opcional con dataframe styling)
                st.dataframe(
                    df_i.rename(columns={"nombre_producto": "Material", "stock_actual": "Stock"}),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Alerta visual de stock bajo (menos de 5 unidades)
                bajo_stock = df_i[df_i['stock_actual'] < 5]
                if not bajo_stock.empty:
                    st.error(f"⚠️ ¡Atención! {len(bajo_stock)} productos con stock bajo.")
            else:
                st.info("El inventario está vacío.")

# --- PÁGINA: INVENTARIO ---
    elif menu == "Inventario":
        st.title("📦 Almacén CEDIS Perote")
        # Definimos 3 pestañas: Stock, Registro de nuevos y el Historial de entradas
        tab1, tab2, tab3 = st.tabs(["📋 Stock Actual", "➕ Nuevo Producto", "🕒 Historial de Movimientos"])

        # PESTAÑA 1: VISUALIZACIÓN Y REABASTECIMIENTO
        with tab1:
            res_i = supabase.table("inventario").select("*").order("nombre_producto").execute()
            if res_i.data:
                for p in res_i.data:
                    with st.expander(f"🛒 {p['nombre_producto']} - Cantidad: {p['stock_actual']}"):
                        c1, c2 = st.columns([1, 2])
                        with c1: 
                            if p['foto_url']: st.image(p['foto_url'], width=150)
                            else: st.info("Sin imagen")
                        with c2:
                            st.write(f"**Precio:** ${p['precio_unitario']}")
                            # Formulario único por producto para evitar conflictos de estado
                            with st.form(key=f"f_stock_{p['id']}"):
                                add = st.number_input("Cantidad que entra al almacén", min_value=0, step=1)
                                if st.form_submit_button("Actualizar Stock"):
                                    if add > 0:
                                        nuevo_total = p['stock_actual'] + add
                                        # Actualizar tabla principal
                                        supabase.table("inventario").update({"stock_actual": nuevo_total}).eq("id", p['id']).execute()
                                        # Registrar en historial con el encargado actual
                                        supabase.table("historial_inventario").insert({
                                            "producto_id": p['id'], 
                                            "usuario_id": st.session_state.usuario_id, 
                                            "cantidad_añadida": add
                                        }).execute()
                                        st.success(f"Se añadieron {add} unidades")
                                        st.rerun()
            else:
                st.info("No hay productos registrados en el inventario.")

        # PESTAÑA 2: FORMULARIO DE NUEVO PRODUCTO
        with tab2:
            st.subheader("Registrar nuevo material en el catálogo")
            with st.form("form_nuevo_producto", clear_on_submit=True):
                nombre_p = st.text_input("Nombre del Producto (ej. Cemento Tolteca)")
                desc_p = st.text_area("Descripción corta")
                precio_p = st.number_input("Precio de Venta Unitario", min_value=0.0, step=0.5)
                stock_p = st.number_input("Stock Inicial", min_value=0, step=1)
                foto_p = st.file_uploader("Subir foto del producto", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("Guardar Producto"):
                    if nombre_p:
                        # Subir foto si existe
                        url_foto = subir_archivo(foto_p, "evidencias", "productos") if foto_p else None
                        
                        nuevo_prod = {
                            "nombre_producto": nombre_p,
                            "descripcion": desc_p,
                            "precio_unitario": precio_p,
                            "stock_actual": stock_p,
                            "foto_url": url_foto
                        }
                        try:
                            supabase.table("inventario").insert(nuevo_prod).execute()
                            st.success(f"✅ {nombre_p} ha sido agregado al inventario.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("El nombre del producto es obligatorio.")

        # PESTAÑA 3: HISTORIAL DE ENTRADAS (QUIÉN Y CUÁNDO)
        with tab3:
            st.subheader("🕒 Log de Reabastecimientos")
            try:
                # Traemos el historial uniendo con el nombre del producto y el nombre del usuario
                res_h = supabase.table("historial_inventario")\
                    .select("fecha_movimiento, cantidad_añadida, inventario(nombre_producto), usuarios(nombre_usuario)")\
                    .order("fecha_movimiento", desc=True).execute()
                
                if res_h.data:
                    datos_tabla = []
                    for h in res_h.data:
                        datos_tabla.append({
                            "Fecha": pd.to_datetime(h['fecha_movimiento']).strftime('%d/%m/%Y %H:%M'),
                            "Producto": h['inventario']['nombre_producto'],
                            "Cantidad": h['cantidad_añadida'],
                            "Encargado": h['usuarios']['nombre_usuario']
                        })
                    st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
                else:
                    st.info("Aún no hay movimientos registrados en el historial.")
            except Exception as e:
                st.error(f"Error al cargar el historial: {e}")

# --- PÁGINA: NUEVA VENTA (CON DESCUENTOS Y DIRECCIÓN DETALLADA) ---
    elif menu == "Nueva Venta":
        st.title("🛒 Nueva Orden de Venta")
        col_selec, col_resumen = st.columns([1, 1])
        
        with col_selec:
            st.subheader("1. Selección de Materiales")
            res_inv = supabase.table("inventario").select("*").gt("stock_actual", 0).execute()
            
            dict_inv = {
                f"{i['nombre_producto']} (Stock: {i['stock_actual']})": i 
                for i in res_inv.data
            }
            
            opciones_prod = list(dict_inv.keys())
            p_sel_label = st.selectbox("Producto/Material", opciones_prod)
            item_seleccionado = dict_inv[p_sel_label]
            
            c_input1, c_input2 = st.columns(2)
            with c_input1:
                c_sel = st.number_input(
                    "Cantidad", 
                    min_value=1, 
                    max_value=int(item_seleccionado['stock_actual']), 
                    value=1
                )
            with c_input2:
                desc_sel = st.number_input("Descuento Total ($)", min_value=0.0, value=0.0, step=10.0)
            precio_bruto = item_seleccionado['precio_unitario'] * c_sel
            subtotal_item = precio_bruto - desc_sel
            
            if desc_sel > 0:
                st.caption(f"Precio Original: ${precio_bruto:,.2f} | Descuento: -${desc_sel:,.2f}")
                st.write(f"**Subtotal Final: :green[${subtotal_item:,.2f}]**")
            
            if subtotal_item < 0:
                st.error("El descuento no puede ser mayor al costo del producto.")
            
            if st.button("➕ Añadir a la Orden"):
                if subtotal_item >= 0:
                    st.session_state.carrito.append({
                        "id": item_seleccionado['id'], 
                        "nombre": item_seleccionado['nombre_producto'], 
                        "precio_base": item_seleccionado['precio_unitario'], 
                        "cantidad": c_sel, 
                        "descuento": desc_sel,
                        "subtotal": subtotal_item
                    })
                    st.toast(f"Añadido: {item_seleccionado['nombre_producto']}")

        with col_resumen:
            st.subheader("2. Resumen de la Orden")
            if st.session_state.carrito:
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[["nombre", "cantidad", "descuento", "subtotal"]])
                subtotal_productos = df_car['subtotal'].sum()
                if st.button("🗑️ Limpiar Orden"):
                    st.session_state.carrito = []
                    st.rerun()
            else:
                st.write("No hay materiales en la orden.")
                subtotal_productos = 0

        st.divider()
        st.subheader("3. Datos de Entrega y Liquidación")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("##### 👤 Cliente")
            res_cli = supabase.table("Clientes").select("id, nombre").execute()
            dict_cli = {c['nombre']: c['id'] for c in res_cli.data}
            c_final_sel = st.selectbox("Buscar Cliente", ["-- AGREGAR CLIENTE NUEVO --"] + list(dict_cli.keys()))
            
            nuevo_cli_nom, nuevo_cli_tel = "", ""
            if c_final_sel == "-- AGREGAR CLIENTE NUEVO --":
                nuevo_cli_nom = st.text_input("Nombre del nuevo cliente")
                nuevo_cli_tel = st.text_input("WhatsApp del nuevo cliente")
            
            fec_e = st.date_input("Fecha Programada")
        
        with c2:
            st.markdown("##### 📍 Dirección Detallada")
            calle = st.text_input("Calle y Número")
            colonia = st.text_input("Colonia")
            municipio = st.text_input("Municipio/Delegación", value="Perote")
            estado = st.text_input("Estado", value="Veracruz")
            # Unimos la dirección para la base de datos
            lug_e_completo = f"{calle}, {colonia}, {municipio}, {estado}"
        
        with c3:
            st.markdown("##### 💰 Totales")
            flete = st.number_input("Flete ($)", min_value=0.0, step=50.0)
            maniobra = st.number_input("Maniobra ($)", min_value=0.0, step=50.0)
            pagado = st.number_input("Pago hoy ($)", min_value=0.0)
            
            # Cálculo del total (Aseguramos que las variables existan arriba)
            total_v = float(subtotal_productos + flete + maniobra)
            credito = total_v - pagado
            
            st.markdown(f"### TOTAL: :green[${total_v:,.2f}]")
            if credito > 0:
                st.warning(f"Saldo Pendiente: ${credito:,.2f}")
            else:
                st.success("Venta Liquidada")
            
            evid = st.file_uploader("Evidencia de Pago", type=["jpg", "png", "pdf"])

        if st.button("✅ PROCESAR VENTA FINAL", use_container_width=True, type="primary"):
            if not st.session_state.carrito:
                st.error("Carrito vacío")
            elif c_final_sel == "-- AGREGAR CLIENTE NUEVO --" and not nuevo_cli_nom:
                st.error("Falta el nombre del cliente nuevo")
            elif not calle or not colonia:
                st.error("Faltan datos de la dirección")
            else:
                target_id = None
                if c_final_sel == "-- AGREGAR CLIENTE NUEVO --":
                    res_new = supabase.table("Clientes").insert({"nombre": nuevo_cli_nom, "telefono": nuevo_cli_tel}).execute()
                    target_id = res_new.data[0]['id']
                else:
                    target_id = dict_cli[c_final_sel]

                if target_id:
                    url_e = subir_archivo(evid, "evidencias", "ventas")
                    v_ins = {
                        "cliente_id": target_id, 
                        "vendedor_id": st.session_state.usuario_id, 
                        "monto_total": total_v, 
                        "monto_credito": credito, 
                        "evidencia_url": url_e, 
                        "fecha_entrega": str(fec_e), 
                        "lugar_entrega": lug_e_completo, 
                        "cargos_adicionales": {"flete": flete, "maniobra": maniobra}, 
                        "estatus_pago": "pagado" if credito <= 0 else "pendiente"
                    }
                    rv = supabase.table("ventas").insert(v_ins).execute()
                    id_v = rv.data[0]['id']
                    
                    for art in st.session_state.carrito:
                        supabase.table("detalles_venta").insert({
                            "venta_id": id_v, 
                            "producto_id": art['id'], 
                            "cantidad": art['cantidad'], 
                            "precio_unitario": art['precio_base'], 
                            "descuento_aplicado": art['descuento'],
                            "subtotal": art['subtotal']
                        }).execute()
                        
                        s_act = supabase.table("inventario").select("stock_actual").eq("id", art['id']).single().execute().data['stock_actual']
                        supabase.table("inventario").update({"stock_actual": s_act - art['cantidad']}).eq("id", art['id']).execute()
                    
                    st.success("¡Venta Exitosa!")
                    st.session_state.carrito = []
                    st.rerun()


    elif menu == "Clientes":
        st.title("👥 Gestión de Clientes y Recibos")
        
        # Definimos las 3 pestañas principales
        tab1, tab2, tab3 = st.tabs(["📊 Cartera General", "🔍 Expediente Detallado", "🧾 Ver Recibos"])
        
        # --- TAB 1: CARTERA GENERAL ---
        with tab1:
            try:
                res_c = supabase.table("Clientes").select("*").execute()
                res_v = supabase.table("ventas").select("cliente_id, monto_total, monto_credito, fecha_venta").execute()
                df_c, df_v = pd.DataFrame(res_c.data), pd.DataFrame(res_v.data)
                
                stats = []
                for _, c in df_c.iterrows():
                    cv = df_v[df_v['cliente_id'] == c['id']]
                    u_compra = pd.to_datetime(cv['fecha_venta'].max()).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not cv.empty else "N/A"
                    
                    stats.append({
                        "Nombre": c['nombre'], 
                        "Dirección": c.get('direccion', 'Sin dirección'),
                        "Saldo Deudor": cv['monto_credito'].sum(), 
                        "Total Compras": cv['monto_total'].sum(), 
                        "Última Compra": u_compra
                    })
                df_final = pd.DataFrame(stats).sort_values("Saldo Deudor", ascending=False)
                st.dataframe(df_final, use_container_width=True, hide_index=True)
            except Exception as e: 
                st.error(f"Error al cargar cartera: {e}")

        # --- TAB 2: EXPEDIENTE DETALLADO ---
        with tab2:
            st.subheader("Consulta de Historial por Cliente")
            res_c_exp = supabase.table("Clientes").select("*").order("nombre").execute()
            dict_c_exp = {c['nombre']: c for c in res_c_exp.data}
            
            c_sel_nom = st.selectbox("Seleccionar Cliente para auditar", list(dict_c_exp.keys()))
            
            if c_sel_nom:
                c_data = dict_c_exp[c_sel_nom]
                st.divider()
                
                col1, col2, col3 = st.columns(3)
                col1.info(f"**Nombre:**\n\n{c_data['nombre']}")
                col2.info(f"**WhatsApp:**\n\n{c_data.get('telefono', 'N/A')}")
                col3.info(f"**Email:**\n\n{c_data.get('email', 'N/A')}")
                
                ventas_c = supabase.table("ventas").select("*, usuarios(nombre_usuario)").eq("cliente_id", c_data['id']).order("fecha_venta", desc=True).execute()
                df_v_c = pd.DataFrame(ventas_c.data)
                
                ids_ventas = [v['id'] for v in ventas_c.data] if ventas_c.data else []
                df_a_c = pd.DataFrame()
                if ids_ventas:
                    abonos_c = supabase.table("abonos").select("*").in_("venta_id", ids_ventas).order("fecha_abono", desc=True).execute()
                    df_a_c = pd.DataFrame(abonos_c.data)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Comprado", f"${df_v_c['monto_total'].sum() if not df_v_c.empty else 0:,.2f}")
                m2.metric("Deuda Actual", f"${df_v_c['monto_credito'].sum() if not df_v_c.empty else 0:,.2f}")
                u_c_f = pd.to_datetime(df_v_c['fecha_venta'].iloc[0]).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not df_v_c.empty else "N/A"
                m3.write(f"**Última Compra:**\n\n{u_c_f}")
                u_a_f = pd.to_datetime(df_a_c['fecha_abono'].iloc[0]).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not df_a_c.empty else "N/A"
                m4.write(f"**Último Abono:**\n\n{u_a_f}")

                st.write("### 📜 Historial de Movimientos")
                t_ventas_tab, t_abonos_tab = st.tabs(["🛍️ Compras", "💰 Abonos Realizados"])
                
                with t_ventas_tab:
                    if not df_v_c.empty:
                        for _, row in df_v_c.iterrows():
                            fecha_mx = pd.to_datetime(row['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M')
                            vendedor = row['usuarios']['nombre_usuario'] if row['usuarios'] else "N/A"
                            folio = str(row['id'])[:8]
                            
                            col_info, col_btn = st.columns([4, 1])
                            with col_info:
                                st.write(f"**Folio:** `{folio}` | **Fecha:** {fecha_mx} | **Vendedor:** {vendedor}")
                                st.caption(f"Total: ${row['monto_total']:,.2f} | Restante: ${row['monto_credito']:,.2f}")
                            with col_btn:
                                if st.button(f"Recibo 🧾", key=f"btn_exp_{row['id']}"):
                                    st.session_state.ver_id = row['id']
                                    st.rerun()
                            st.divider()
                    else: st.write("No hay registros.")
                
                with t_abonos_tab:
                    if not df_a_c.empty:
                        df_a_c['fecha_mx'] = pd.to_datetime(df_a_c['fecha_abono']).dt.tz_convert('America/Mexico_City').dt.strftime('%d/%m/%Y %H:%M')
                        cols_a = [c for c in ['fecha_mx', 'monto_abono', 'forma_pago', 'referencia'] if c in df_a_c.columns]
                        st.dataframe(df_a_c[cols_a], use_container_width=True, hide_index=True)
                    else: st.write("No hay abonos.")

        # --- TAB 3: BUSCADOR GENERAL DE RECIBOS ---
        with tab3:
            st.subheader("Generación de Recibos")
            res_rec = supabase.table("ventas").select("id, fecha_venta, monto_total, Clientes(nombre)").order("fecha_venta", desc=True).limit(20).execute()
            for r in res_rec.data:
                fecha_mx = pd.to_datetime(r['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y')
                col_btn, col_info = st.columns([1, 4])
                with col_btn:
                    if st.button(f"Ver 📄", key=f"btn_list_{r['id']}"):
                        st.session_state.ver_id = r['id']
                        st.rerun()
                with col_info:
                    st.write(f"**{r['Clientes']['nombre']}** - ${r['monto_total']:,.2f} ({fecha_mx})")

    # --- LÓGICA DE VISUALIZACIÓN DEL RECIBO (GLOBAL) ---
    if 'ver_id' in st.session_state:
        st.divider()
        col_tit, col_close = st.columns([5, 1])
        with col_tit: st.subheader("🧾 Vista de Nota de Venta")
        with col_close: 
            if st.button("❌ Cerrar"):
                del st.session_state.ver_id
                st.rerun()
        
        # Consulta detallada con relación al inventario
        vd = supabase.table("ventas").select("*, Clientes(*), usuarios(nombre_usuario)").eq("id", st.session_state.ver_id).single().execute().data
        items = supabase.table("detalles_venta").select("*, inventario(nombre_producto)").eq("venta_id", vd['id']).execute().data
        
        fecha_v_mx = pd.to_datetime(vd['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M')
        st.markdown(f"### CEDIS PEROTE")
        st.write(f"**Folio:** `{vd['id']}`")
        st.write(f"**Fecha:** {fecha_v_mx} | **Vendedor:** {vd['usuarios']['nombre_usuario']}")
        st.write(f"**Cliente:** {vd['Clientes']['nombre']} | **Entrega:** {vd['lugar_entrega']}")
        
        # TABLA DE MATERIALES CON DESCUENTO
        # Usamos i.get('descuento_aplicado', 0) por si hay registros viejos sin esa columna
        df_items = pd.DataFrame([
            {
                "Material": i['inventario']['nombre_producto'], 
                "Cant": i['cantidad'], 
                "Precio U.": f"${i['precio_unitario']:,.2f}",
                "Desc. Aplicado": f"-${i.get('descuento_aplicado', 0):,.2f}",
                "Subtotal": f"${i['subtotal']:,.2f}"
            } for i in items
        ])
        st.table(df_items)

        # Cargos Logística
        cargos = vd.get('cargos_adicionales', {})
        flete = cargos.get('flete', 0.0)
        maniobra = cargos.get('maniobra', 0.0)
        
        if flete > 0 or maniobra > 0:
            st.write("---")
            st.write("**Cargos de Logística:**")
            cf, cm = st.columns(2)
            cf.write(f"Flete: ${flete:,.2f}")
            cm.write(f"Maniobra: ${maniobra:,.2f}")
        
        st.write("---")
        st.write(f"## TOTAL FINAL: ${vd['monto_total']:,.2f}")
        st.write(f"**Pagado hoy:** ${vd['monto_total'] - vd['monto_credito']:,.2f} | **Restante:** ${vd['monto_credito']:,.2f}")
        st.info("💡 Tip: Presiona Ctrl+P para guardar como PDF.")


# --- PÁGINA: REGISTRAR ABONO (COBRANZA CON EVIDENCIA) ---
    elif menu == "Registrar Abono":
        st.title("💸 Cobranza CEDIS Perote")
        
        # Consultar ventas que tienen saldo pendiente
        res_v = supabase.table("ventas").select("id, monto_credito, Clientes(nombre)").gt("monto_credito", 0).execute()
        
        if res_v.data:
            # Diccionario para identificar la deuda seleccionada
            dict_d = {f"{v['Clientes']['nombre']} (Saldo: ${v['monto_credito']})": v for v in res_v.data}
            
            # Selector fuera del form para reactividad
            v_s_label = st.selectbox("Seleccionar Deuda Pendiente", list(dict_d.keys()))
            deuda_seleccionada = dict_d[v_s_label]
            
            st.divider()
            
            with st.form("f_abono", clear_on_submit=True):
                c1, c2 = st.columns(2)
                
                with c1:
                    ab = st.number_input(
                        "Monto del Abono ($)", 
                        min_value=1.0, 
                        max_value=float(deuda_seleccionada['monto_credito']),
                        step=100.0
                    )
                    forma_pago = st.selectbox(
                        "Forma de Pago", 
                        ["Efectivo", "Transferencia", "Tarjeta Débito/Crédito", "Depósito Bancario"]
                    )
                
                with c2:
                    evid_abono = st.file_uploader("Comprobante del Abono", type=["jpg", "png", "jpeg", "pdf"])
                    referencia = st.text_input("Referencia / Notas (Opcional)")

                if st.form_submit_button("✅ Registrar Cobro"):
                    # 1. Subir evidencia si existe
                    url_evidencia = subir_archivo(evid_abono, "evidencias", "abonos") if evid_abono else None
                    
                    # 2. Insertar el registro del abono
                    nuevo_abono = {
                        "venta_id": deuda_seleccionada['id'],
                        "vendedor_id": st.session_state.usuario_id,
                        "monto_abono": ab,
                        "forma_pago": forma_pago,
                        "evidencia_url": url_evidencia,
                        "referencia": referencia
                    }
                    
                    try:
                        # Registrar abono
                        supabase.table("abonos").insert(nuevo_abono).execute()
                        
                        # Actualizar el saldo pendiente en la tabla de ventas
                        nuevo_saldo = deuda_seleccionada['monto_credito'] - ab
                        # Si el saldo llega a 0, podrías actualizar también un estatus de pago
                        update_data = {"monto_credito": nuevo_saldo}
                        if nuevo_saldo <= 0:
                            update_data["estatus_pago"] = "pagado"
                            
                        supabase.table("ventas").update(update_data).eq("id", deuda_seleccionada['id']).execute()
                        
                        st.success(f"Abono de ${ab} registrado con éxito para {deuda_seleccionada['Clientes']['nombre']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar abono: {e}")
        else:
            st.info("No hay deudas pendientes por cobrar actualmente.")

# --- PÁGINA: REGISTRO DE CLIENTES ---
    elif menu == "Registro de Clientes":
        st.title("➕ Alta de Clientes - CEDIS Perote")
        st.write("Complete los datos para dar de alta a un nuevo cliente en el sistema.")
        
        with st.form("f_registro_cliente", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                n = st.text_input("Nombre / Razón Social*", help="Campo obligatorio")
                t = st.text_input("Teléfono WhatsApp", placeholder="Ej. 2281234567")
            
            with col_b:
                e = st.text_input("Correo Electrónico")
                d = st.text_input("Dirección Completa", placeholder="Calle, Número, Colonia, Ciudad")
            
            st.caption("(*) Campos obligatorios")
            
            if st.form_submit_button("Guardar Cliente"):
                if n:  # Validar que al menos el nombre esté presente
                    nuevo_cliente = {
                        "nombre": n, 
                        "telefono": t, 
                        "email": e, 
                        "direccion": d
                    }
                    try:
                        supabase.table("Clientes").insert(nuevo_cliente).execute()
                        st.success(f"✅ ¡Cliente '{n}' registrado exitosamente!")
                    except Exception as err:
                        st.error(f"Error al guardar en la base de datos: {err}")
                else:
                    st.warning("⚠️ Por favor, ingrese al menos el nombre del cliente.")
    
    elif menu == "Flota y Unidades":
            st.title("🚛 Gestión de Flota - CEDIS Perote")
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Inventario", 
                "➕ Alta de Unidad", 
                "🛠️ Mantenimiento", 
                "⛽ Combustible"
            ])

# --- TAB 1: INVENTARIO DE UNIDADES (CON MÉTRICAS FINANCIERAS) ---
            with tab1:
                # 1. Obtenemos datos de Unidades y de todo el historial de Combustible
                res_u = supabase.table("unidades").select("*").order("nombre_unidad").execute()
                res_c_total = supabase.table("combustible_unidades").select("costo_total").execute()
                
                df_u = pd.DataFrame(res_u.data)
                df_c_total = pd.DataFrame(res_c_total.data)

                if not df_u.empty:
                    # 2. Cálculos de métricas con manejo de errores
                    total_unidades = len(df_u)
                    
                    # Unidades en taller (filtrado seguro)
                    unidades_taller = len(df_u[df_u['estado'].str.contains("reparación", case=False, na=False)])
                    
                    # Gasto de Mantenimiento (Suma de la columna ultimo_costo_reparacion)
                    # Usamos fillna(0) para evitar errores si hay celdas vacías
                    gasto_mant = df_u['ultimo_costo_reparacion'].fillna(0).sum()
                    
                    # Gasto de Gasolina (Suma de todo el histórico)
                    gasto_gas = df_c_total['costo_total'].fillna(0).sum() if not df_c_total.empty else 0.0

                    # 3. Visualización de métricas en 4 columnas
                    c1, c2, c3, c4 = st.columns(4)
                    
                    c1.metric("Total Unidades", total_unidades)
                    c2.metric("En Taller", unidades_taller)
                    c3.metric("Gasto Mant. Total", f"${gasto_mant:,.2f}")
                    c4.metric("Gasto Gasolina Total", f"${gasto_gas:,.2f}")

                    st.divider()
                    
                    # 4. Iteración de unidades para el detalle (Expanders)
                    for _, u in df_u.iterrows():
                        with st.expander(f"🚚 {u['nombre_unidad']} - {u['placas']} ({u['estado'].upper()})"):
                            # Aquí va tu código previo de col_a, col_b y las sub-pestañas de historial
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Serie:** {u['serie']} | **Color:** {u['color']}")
                                st.write(f"**Responsable:** {u['responsable_fijo']}")
                            with col_b:
                                st.write(f"**KM Actual:** {u.get('kilometraje_actual', 0):,} km")
                                if u.get('evidencia_estado_url'):
                                    st.image(u['evidencia_estado_url'], width=200)
                            
                            st.divider()
                            st.subheader(f"📜 Historial Detallado: {u['nombre_unidad']}")
                            
                            # Sub-pestañas de historial detallado
                            sub_t1, sub_t2, sub_t3 = st.tabs(["🛠️ Mantenimiento", "⛽ Combustible", "📦 Envíos"])
                            
                            with sub_t1:
                                res_hm = supabase.table("historial_unidades").select("*").eq("unidad_id", u['id']).order("fecha_ingreso", desc=True).execute()
                                if res_hm.data:
                                    st.dataframe(pd.DataFrame(res_hm.data)[['fecha_ingreso', 'costo_total', 'descripcion_falla']], use_container_width=True, hide_index=True)
                                else: st.info("Sin historial.")

                            with sub_t2:
                                res_hg = supabase.table("combustible_unidades").select("*").eq("unidad_id", u['id']).order("fecha", desc=True).execute()
                                if res_hg.data:
                                    st.dataframe(pd.DataFrame(res_hg.data)[['fecha', 'litros', 'costo_total']], use_container_width=True, hide_index=True)
                                else: st.info("Sin historial.")

                            with sub_t3:
                                res_he = supabase.table("envios").select("*, ventas(Clientes(nombre))").eq("unidad_id", u['id']).order("fecha_registro", desc=True).execute()
                                if res_he.data:
                                    env_list = [{"Fecha": e['fecha_registro'][:10], "Cliente": e['ventas']['Clientes']['nombre'], "Estatus": e['estatus']} for e in res_he.data]
                                    st.table(pd.DataFrame(env_list))
                                else: st.info("Sin envíos.")
                else:
                    st.warning("No hay unidades registradas en el sistema.")

            # --- TAB 2: ALTA DE UNIDAD ---
            with tab2:
                st.subheader("Registrar Nueva Unidad")
                with st.form("f_nueva_unidad", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        n_u = st.text_input("Nombre de la Unidad")
                        p_u = st.text_input("Placas")
                        t_u = st.selectbox("Tipo", ["Torton", "Camioneta 3.5", "Pick-up", "Particular"])
                    with c2:
                        col_u = st.text_input("Color")
                        resp_u = st.text_input("Responsable Asignado")
                        km_u = st.number_input("Kilometraje Inicial", min_value=0)

                    if st.form_submit_button("Guardar Unidad"):
                        data_u = {
                            "nombre_unidad": n_u, "placas": p_u, "tipo": t_u, 
                            "color": col_u, "responsable_fijo": resp_u, "kilometraje_actual": km_u
                        }
                        supabase.table("unidades").insert(data_u).execute()
                        st.success("Unidad registrada")
                        st.rerun()

    # --- TAB 3: MANTENIMIENTO (CAMBIO DE ESTADO AUTOMÁTICO) ---
            with tab3:
                st.subheader("🛠️ Control de Taller y Reparaciones")
                if not df_u.empty:
                    # Diccionario para obtener info de la unidad
                    u_list = {f"{u['nombre_unidad']} ({u['placas']})": u for u in res_u.data}
                    u_sel_nom = st.selectbox("Seleccionar Unidad", list(u_list.keys()))
                    u_info = u_list[u_sel_nom]
                    
                    col_m1, col_m2 = st.columns(2)
                    
                    # --- LÓGICA DE ENTRADA AL TALLER ---
                    with col_m1:
                        st.markdown("### 📥 Registrar Entrada")
                        with st.form("f_entrada_taller", clear_on_submit=True):
                            f_in = st.date_input("Fecha de Ingreso")
                            taller = st.text_input("Taller / Mecánico")
                            falla = st.text_area("Motivo de ingreso / Falla")
                            
                            if st.form_submit_button("🔨 Enviar a Reparación"):
                                # 1. Cambiamos el estado de la unidad a 'en reparación'
                                supabase.table("unidades").update({
                                    "estado": "en reparación",
                                    "nota_estado": falla,
                                    "ultima_entrada_taller": str(f_in),
                                    "encargado_reparacion": taller
                                }).eq("id", u_info['id']).execute()
                                
                                st.success(f"Unidad {u_info['nombre_unidad']} marcada 'En Reparación'")
                                st.rerun()

                    # --- LÓGICA DE SALIDA DEL TALLER ---
                    with col_m2:
                        st.markdown("### 📤 Registrar Salida")
                        # Solo habilitamos salida si la unidad está realmente en reparación
                        if u_info['estado'] == "en reparación":
                            with st.form("f_salida_taller", clear_on_submit=True):
                                f_out = st.date_input("Fecha de Salida")
                                costo = st.number_input("Costo Final de Reparación ($)", min_value=0.0, step=100.0)
                                evid_r = st.file_uploader("Evidencia / Factura", type=["jpg", "png", "pdf"])
                                
                                if st.form_submit_button("✅ Finalizar Reparación"):
                                    url_r = subir_archivo(evid_r, "evidencias", "reparaciones") if evid_r else None
                                    
                                    # 1. Devolvemos la unidad a estado 'activo' y actualizamos costos
                                    supabase.table("unidades").update({
                                        "estado": "activo",
                                        "nota_estado": "Reparación finalizada",
                                        "ultima_salida_taller": str(f_out),
                                        "ultimo_costo_reparacion": costo
                                    }).eq("id", u_info['id']).execute()
                                    
                                    # 2. Guardamos en el historial para auditoría de costos
                                    hist_data = {
                                        "unidad_id": u_info['id'],
                                        "tipo_movimiento": "Reparación",
                                        "fecha_ingreso": u_info['ultima_entrada_taller'],
                                        "fecha_salida": str(f_out),
                                        "costo_total": costo,
                                        "descripcion_falla": u_info['nota_estado'],
                                        "encargado_taller": u_info['encargado_reparacion'],
                                        "evidencia_url": url_r
                                    }
                                    supabase.table("historial_unidades").insert(hist_data).execute()
                                    
                                    st.success("Unidad reactivada y costo registrado.")
                                    st.rerun()
                        else:
                            st.info("Esta unidad se encuentra actualmente: **ACTIVA**. No requiere registro de salida.")
                else:
                    st.warning("No hay unidades registradas.")

            # --- TAB 4: COMBUSTIBLE (CORREGIDA) ---
            with tab4:
                st.subheader("⛽ Carga de Gasolina")
                if not df_u.empty:
                    # Diccionario para obtener info rápida de la unidad seleccionada
                    u_c_dict = {f"{u['nombre_unidad']} ({u['placas']})": u for u in res_u.data}
                    u_c_sel = st.selectbox("Seleccionar Unidad para Gasolina", list(u_c_dict.keys()))
                    u_info = u_c_dict[u_c_sel]

                    with st.form("f_combustible", clear_on_submit=True):
                        c_g1, c_g2 = st.columns(2)
                        with c_g1:
                            f_g = st.date_input("Fecha Carga")
                            # Usamos int() para asegurar que el KM sea un número entero
                            km_actual_bd = int(u_info.get('kilometraje_actual', 0))
                            km_g = st.number_input("Kilometraje al cargar", min_value=km_actual_bd, value=km_actual_bd)
                        with c_g2:
                            lits = st.number_input("Litros", min_value=1.0, step=0.1)
                            pago = st.number_input("Costo Total ($)", min_value=1.0, step=10.0)
                            ticket = st.file_uploader("Ticket", type=["jpg", "png", "jpeg"])

                        if st.form_submit_button("Registrar Carga"):
                            # Cálculo del precio por litro antes de insertar
                            ppl = pago / lits if lits > 0 else 0
                            
                            # Subida de archivo (usando tu función existente)
                            url_t = subir_archivo(ticket, "evidencias", "combustible") if ticket else None
                            
                            try:
                                # Preparar los datos EXACTAMENTE como están en SQL
                                data_g = {
                                    "unidad_id": u_info['id'], 
                                    "fecha": str(f_g),
                                    "kilometraje_registro": int(km_g), 
                                    "litros": float(lits),
                                    "costo_total": float(pago), 
                                    "precio_por_litro": float(ppl),
                                    "ticket_url": url_t,
                                    "vendedor_id": st.session_state.usuario_id
                                }
                                
                                # Intentar inserción
                                supabase.table("combustible_unidades").insert(data_g).execute()
                                
                                # Actualizar el kilometraje en la tabla de unidades
                                supabase.table("unidades").update({"kilometraje_actual": km_g}).eq("id", u_info['id']).execute()
                                
                                st.success(f"✅ Carga registrada con éxito por ${pago:,.2f}")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error de base de datos: {e}")
                else:
                    st.info("Registre una unidad en la pestaña 'Alta de Unidad' primero.")

    elif menu == "Logística y Envíos":
            st.title("🚚 Control de Entregas - CEDIS Perote")
            tab_pend, tab_hist = st.tabs(["📦 Envíos Pendientes", "📜 Historial de Rutas"])

            # 1. Obtención de datos necesarios
            # Consultamos qué ventas ya tienen un envío en estado final para excluirlas de "Pendientes"
            res_envios_finalizados = supabase.table("envios").select("venta_id").in_("estatus", ["terminado", "cancelado", "devuelto"]).execute()
            ids_excluir = [e['venta_id'] for e in res_envios_finalizados.data]

            # Traemos todas las ventas y filtramos las que no han sido finalizadas
            res_v_raw = supabase.table("ventas").select("*, Clientes(nombre)").order("fecha_entrega").execute()
            ventas_filtradas = [v for v in res_v_raw.data if v['id'] not in ids_excluir]
            
            res_unid = supabase.table("unidades").select("*").eq("estado", "activo").execute()
            res_oper = supabase.table("usuarios").select("id, nombre_usuario").execute()
            
            # --- TAB 1: GESTIÓN DE ENVÍOS PENDIENTES ---
            with tab_pend:
                st.subheader("Asignación y Despacho")
                
                # Métricas rápidas
                st.write(f"📋 **Entregas pendientes por programar:** {len(ventas_filtradas)}")
                
                ventas_opciones = {f"Folio: {v['id'][:8]} - {v['Clientes']['nombre']} ({v['fecha_entrega']})": v for v in ventas_filtradas}
                
                if ventas_opciones:
                    v_sel_label = st.selectbox("Seleccionar Venta para Enviar", list(ventas_opciones.keys()))
                    v_data = ventas_opciones[v_sel_label]
                    
                    st.info(f"📍 **Destino:** {v_data['lugar_entrega']}")
                    
                    with st.form("f_asignar_envio"):
                        c_l1, c_l2 = st.columns(2)
                        with c_l1:
                            u_opts = {f"{u['nombre_unidad']} ({u['placas']})": u['id'] for u in res_unid.data}
                            u_envio = st.selectbox("Asignar Unidad", list(u_opts.keys()))
                            
                            oper_opts = {o['nombre_usuario']: o['id'] for o in res_oper.data}
                            op_envio = st.selectbox("Operador Responsable", list(oper_opts.keys()))
                        
                        with c_l2:
                            acomp = st.text_input("Acompañantes / Auxiliares", placeholder="Ej. Juan Pérez, Luis Gómez")
                            # Agregamos "de regreso" y "terminado" aunque usualmente inician en "en preparacion"
                            estatus_e = st.selectbox("Estatus Inicial", ["en preparacion", "listo para enviar", "enviado"])
                        
                        evid_s = st.file_uploader("Evidencia de Salida (Carga lista)", type=["jpg", "png"])
                        notas_l = st.text_area("Notas de Logística")

                        if st.form_submit_button("🚀 Confirmar Despacho"):
                            url_s = subir_archivo(evid_s, "evidencias", "envios") if evid_s else None
                            
                            envio_ins = {
                                "venta_id": v_data['id'],
                                "unidad_id": u_opts[u_envio],
                                "operador_id": oper_opts[op_envio],
                                "acompanantes": acomp,
                                "estatus": estatus_e,
                                "notas_logistica": notas_l,
                                "evidencia_salida_url": url_s,
                                "fecha_salida": str(pd.Timestamp.now(tz='America/Mexico_City')) if estatus_e == "enviado" else None
                            }
                            supabase.table("envios").insert(envio_ins).execute()
                            
                            # Si el estatus inicial es enviado, la unidad se bloquea
                            if estatus_e == "enviado":
                                supabase.table("unidades").update({"estado": "en ruta"}).eq("id", u_opts[u_envio]).execute()
                            
                            st.success(f"Logística registrada para folio {v_data['id'][:8]}")
                            st.rerun()
                else:
                    st.info("✅ No hay ventas pendientes de asignación. Todas las rutas están al día.")

            # --- TAB 2: HISTORIAL Y SEGUIMIENTO DETALLADO ---
            with tab_hist:
                st.subheader("📋 Seguimiento de Rutas por Venta")
                
                res_env = supabase.table("envios").select("*, ventas(*, Clientes(*)), unidades(*), usuarios(*)").order("fecha_registro", desc=True).execute()
                
                if res_env.data:
                    for en in res_env.data:
                        cliente = en['ventas']['Clientes']['nombre']
                        fecha_v = pd.to_datetime(en['ventas']['fecha_venta']).strftime('%d/%m/%Y')
                        folio_v = en['ventas']['id'][:8]
                        estatus_actual = en['estatus'].upper()
                        
                        with st.expander(f"👤 {cliente} | 📅 {fecha_v} | 🧾 Venta: {folio_v} | 🚩 [{estatus_actual}]"):
                            col_det, col_act = st.columns([2, 1])
                            
                            with col_det:
                                st.markdown(f"**Unidad:** {en['unidades']['nombre_unidad']} ({en['unidades']['placas']})")
                                st.markdown(f"**Operador:** {en['usuarios']['nombre_usuario']}")
                                st.markdown(f"**Destino:** {en['ventas']['lugar_entrega']}")
                                
                                res_h = supabase.table("historial_estatus_envios").select("*").eq("envio_id", en['id']).order("fecha_cambio", desc=True).execute()
                                if res_h.data:
                                    st.caption("🕒 Línea de tiempo de estatus:")
                                    for h in res_h.data:
                                        f_h = pd.to_datetime(h['fecha_cambio']).tz_convert('America/Mexico_City').strftime('%d/%m %H:%M')
                                        st.write(f"• `{f_h}`: **{h['estatus_nuevo'].upper()}**")
                            
                            with col_act:
                                st.markdown("##### Actualizar Estatus")
                                with st.form(f"form_status_{en['id']}"):
                                    # Lista de estados actualizada con "de regreso" y "terminado"
                                    opciones_estatus = [
                                        "en preparacion", "listo para enviar", "enviado", 
                                        "retrasado", "recibido", "de regreso", "terminado", 
                                        "cancelado", "devuelto"
                                    ]
                                    
                                    idx_actual = opciones_estatus.index(en['estatus']) if en['estatus'] in opciones_estatus else 0
                                    nuevo_est = st.selectbox("Nuevo Estado", opciones_estatus, index=idx_actual)
                                    nota_hist = st.text_input("Nota del cambio", placeholder="Ej. Entregado, iniciando regreso")
                                    
                                    if st.form_submit_button("Actualizar 💾"):
                                        if nuevo_est != en['estatus']:
                                            # 1. Registro en historial de auditoría
                                            supabase.table("historial_estatus_envios").insert({
                                                "envio_id": en['id'],
                                                "estatus_anterior": en['estatus'],
                                                "estatus_nuevo": nuevo_est,
                                                "usuario_id": st.session_state.usuario_id,
                                                "notas": nota_hist
                                            }).execute()
                                            
                                            upd_envio = {"estatus": nuevo_est}
                                            
                                            # --- LÓGICA DE UNIDADES (CORREGIDA) ---
                                            # Si está enviado, retrasado o de regreso, la unidad sigue 'en ruta'
                                            if nuevo_est in ["enviado", "retrasado", "de regreso", "recibido"]:
                                                supabase.table("unidades").update({"estado": "en ruta"}).eq("id", en['unidad_id']).execute()
                                            
                                            # SOLO al terminar, cancelar o devolver, la unidad vuelve a estar 'activo'
                                            elif nuevo_est in ["terminado", "cancelado", "devuelto"]:
                                                supabase.table("unidades").update({
                                                    "estado": "activo",
                                                    "nota_estado": f"Liberada tras envío {en['id'][:8]}"
                                                }).eq("id", en['unidad_id']).execute()
                                                
                                                if nuevo_est == "terminado":
                                                    upd_envio["fecha_recepcion"] = str(pd.Timestamp.now(tz='America/Mexico_City'))

                                            # Actualizar el registro del envío
                                            supabase.table("envios").update(upd_envio).eq("id", en['id']).execute()
                                            
                                            st.success(f"Estatus actualizado a {nuevo_est.upper()}")
                                            st.rerun()
                else:
                    st.info("No hay registros de envíos en el historial.")
                    
    elif menu == "Gestión de Gastos":
            st.title("💰 Control de Gastos - CEDIS Perote")
            tab_reg, tab_hist = st.tabs(["➕ Registrar Gasto", "📜 Historial y Auditoría"])

            # Consultas base
            res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
            dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}

            # --- TAB 1: REGISTRO DE GASTOS ---
            with tab_reg:
                with st.form("f_nuevo_gasto", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        t_gasto = st.selectbox("Tipo de Gasto", [
                            "Impuestos", "Salarios", "Compra de Mercancía", "Servicios (Luz/Agua)", 
                            "Mantenimiento", "Publicidad", "Herramientas", "Viáticos", "Renta"
                        ])
                        sub_g = st.selectbox("Clasificación Extra", [
                            "Gasto General", "Gasto por Comprobar", "Gasto Reembolsable", "Pago a Proveedor"
                        ])
                        monto_g = st.number_input("Monto ($)", min_value=0.0, step=100.0)
                        
                        # NUEVO: Selector de responsable desde la tabla de usuarios
                        responsable_nom = st.selectbox("Responsable del Gasto", list(dict_users.keys()))
                        responsable_id = dict_users[responsable_nom]
                    
                    with c2:
                        estatus_g = st.selectbox("Estado del Gasto", ["Pagado", "Pendiente", "En Revisión"])
                        evid_g = st.file_uploader("Evidencia (Ticket/Factura)", type=["jpg", "png", "pdf"])
                        desc_g = st.text_area("Descripción del Gasto")

                    if st.form_submit_button("Guardar Gasto"):
                        url_g = subir_archivo(evid_g, "evidencias", "gastos") if evid_g else None
                        
                        ins_data = {
                            "usuario_id": responsable_id, # Ahora usamos el ID del responsable seleccionado
                            "tipo_gasto": t_gasto,
                            "subcategoria": sub_g,
                            "monto": monto_g,
                            "descripcion": desc_g,
                            "estatus_gasto": estatus_g,
                            "evidencia_url": url_g
                        }
                        supabase.table("gastos").insert(ins_data).execute()
                        st.success(f"✅ Gasto registrado a nombre de {responsable_nom}")
                        st.rerun()

            # --- TAB 2: HISTORIAL Y AUDITORÍA ---
            with tab_hist:
                st.subheader("Buscador de Gastos")
                # Traemos el nombre del usuario asignado para mostrarlo en el historial
                res_gastos = supabase.table("gastos").select("*, usuarios(nombre_usuario)").order("fecha_registro", desc=True).execute()
                
                if res_gastos.data:
                    for g in res_gastos.data:
                        # Título del expander con información clave
                        with st.expander(f"💰 {g['tipo_gasto']} - ${g['monto']:,.2f} ({g['fecha_gasto']}) - {g['estatus_gasto']}"):
                            col_i, col_a = st.columns([2, 1])
                            
                            with col_i:
                                # Aquí se verá el nombre del responsable que seleccionaste arriba
                                st.write(f"**Responsable:** {g['usuarios']['nombre_usuario']}")
                                st.write(f"**Categoría:** {g['subcategoria']}")
                                st.write(f"**Descripción:** {g['descripcion']}")
                                if g['evidencia_url']:
                                    st.link_button("Ver Evidencia 📄", g['evidencia_url'])
                                
                                st.caption("🕒 Historial de cambios:")
                                res_h_g = supabase.table("historial_gastos").select("*, usuarios(nombre_usuario)").eq("gasto_id", g['id']).order("fecha_cambio").execute()
                                for h in res_h_g.data:
                                    st.write(f"- `{h['fecha_cambio'][:16]}`: {h['estatus_anterior']} ➔ **{h['estatus_nuevo']}** ({h['usuarios']['nombre_usuario']})")

                            with col_a:
                                st.markdown("##### Actualizar Estado")
                                with st.form(f"f_upd_gasto_{g['id']}"):
                                    nuevo_est = st.selectbox("Cambiar a:", ["Pagado", "Pendiente", "Reembolsado", "Rechazado"], key=f"sel_{g['id']}")
                                    nota_upd = st.text_input("Nota del cambio")
                                    if st.form_submit_button("Actualizar 💾"):
                                        supabase.table("historial_gastos").insert({
                                            "gasto_id": g['id'],
                                            "estatus_anterior": g['estatus_gasto'],
                                            "estatus_nuevo": nuevo_est,
                                            "usuario_id": st.session_state.usuario_id, # Auditoría: quién cambió el estatus
                                            "comentario": nota_upd
                                        }).execute()
                                        
                                        supabase.table("gastos").update({"estatus_gasto": nuevo_est}).eq("id", g['id']).execute()
                                        st.rerun()
                else:
                    st.info("No hay gastos registrados.")
    
    elif menu == "Reportes":
        st.title("📊 Dashboard Operativo y Financiero")
        
        # --- FILTRO DE FECHAS ---
        st.subheader("Filtro de Período")
        col_f1, col_f2 = st.columns([1, 2])
        
        with col_f1:
            # CORRECCIÓN: Usamos datetime.date.today() de forma segura
            try:
                today = datetime.date.today()
            except NameError:
                import datetime
                today = datetime.date.today()
                
            hace_un_mes = today - datetime.timedelta(days=30)
            
            # Selector de rango
            rango = st.date_input("Selecciona el rango", [hace_un_mes, today])
        
        # Validamos que el usuario haya seleccionado ambas fechas (inicio y fin)
        if isinstance(rango, list) or isinstance(rango, tuple):
            if len(rango) == 2:
                f_inicio, f_fin = rango
                
                # --- CONSULTAS A SUPABASE ---
                # 1. Ventas
                res_v = supabase.table("ventas").select("*")\
                    .gte("fecha_venta", f_inicio.isoformat())\
                    .lte("fecha_venta", f_fin.isoformat()).execute()
                df_v = pd.DataFrame(res_v.data)

                # 2. Gastos Generales
                res_g = supabase.table("gastos").select("*")\
                    .gte("fecha_gasto", f_inicio.isoformat())\
                    .lte("fecha_gasto", f_fin.isoformat()).execute()
                df_g = pd.DataFrame(res_g.data)

                # 3. Mantenimiento de Unidades
                res_m = supabase.table("historial_unidades").select("costo_total")\
                    .gte("fecha_ingreso", f_inicio.isoformat())\
                    .lte("fecha_ingreso", f_fin.isoformat()).execute()
                df_m = pd.DataFrame(res_m.data)

                # 4. Combustible
                res_gas = supabase.table("combustible_unidades").select("costo_total")\
                    .gte("fecha", f_inicio.isoformat())\
                    .lte("fecha", f_fin.isoformat()).execute()
                df_gas = pd.DataFrame(res_gas.data)

                # --- PROCESAMIENTO DE DATOS ---
                total_ingresos = df_v['monto_total'].astype(float).sum() if not df_v.empty else 0.0
                total_ventas_count = len(df_v)
                cartera_pendiente = df_v['monto_credito'].astype(float).sum() if not df_v.empty else 0.0

                g_generales = df_g['monto'].sum() if not df_g.empty else 0.0
                g_mantenimiento = df_m['costo_total'].sum() if not df_m.empty else 0.0
                g_gasolina = df_gas['costo_total'].sum() if not df_gas.empty else 0.0
                
                total_egresos = g_generales + g_mantenimiento + g_gasolina
                utilidad = total_ingresos - total_egresos

                # --- SCORECARDS ---
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("💰 Ventas Totales", f"${total_ingresos:,.2f}")
                c2.metric("📦 Órdenes", f"{total_ventas_count}")
                c3.metric("💳 Cartera Pendiente", f"${cartera_pendiente:,.2f}", delta_color="inverse")

                c4, c5, c6 = st.columns(3)
                c4.metric("📉 Gasto Total", f"${total_egresos:,.2f}", delta_color="inverse")
                c5.metric("⚖️ Utilidad Neta", f"${utilidad:,.2f}")
                c6.metric("⛽ Gasolina", f"${g_gasolina:,.2f}")

                st.divider()
                
                # Gráfica de comparación rápida
                if total_ingresos > 0 or total_egresos > 0:
                    st.subheader("📊 Comparativo Ingresos vs Gastos")
                    df_comp = pd.DataFrame({
                        "Concepto": ["Ingresos", "Egresos"],
                        "Monto": [total_ingresos, total_egresos]
                    })
                    st.bar_chart(df_comp.set_index("Concepto"))

            else:
                st.info("Por favor, selecciona la fecha de fin en el calendario.")     