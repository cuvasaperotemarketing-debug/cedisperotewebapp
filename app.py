import streamlit as st
import pandas as pd
from supabase import create_client
import datetime

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
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
                
from datetime import datetime

def subir_archivo(archivo, bucket, folder):
    if archivo is not None:
        try:
            # 1. Generar la ruta técnica del archivo
            nombre_archivo = f"{folder}/{datetime.now().strftime('%Y%m%d%H%M%S')}_{archivo.name}"
            
            # 2. Ejecutar la subida (Upload)
            # Usar getvalue() es correcto para Streamlit
            supabase.storage.from_(bucket).upload(
                path=nombre_archivo, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type}
            )
            
            # 3. Obtener la URL Pública
            # Aseguramos que devuelva un string para evitar el error de TypeError previo
            res_url = supabase.storage.from_(bucket).get_public_url(nombre_archivo)
            
            # Si el resultado es un objeto (común en versiones nuevas), extraemos la URL
            url_final = res_url if isinstance(res_url, str) else res_url.get('publicURL', res_url)
            
            return str(url_final)
            
        except Exception as e:
            # Imprimimos el error en consola para saber qué falló (Permisos, Bucket lleno, etc.)
            print(f"❌ Error al subir archivo: {e}")
            return None
    return None

if st.session_state.rol is None:
    login()
    st.info("Por favor, inicia sesión con tus credenciales de CEDIS Perote para continuar.")
else:
    rol, nombre = st.session_state.rol, st.session_state.nombre_usuario
    opciones = ["Inventario", "Nueva Venta", "Registrar Abono", "Clientes","Flota y Unidades","Logística y Envíos","Gestión de Gastos","Gestión de Ventas","Gestión de Sedes"]
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
        tab1, tab2, tab3 = st.tabs(["📋 Stock Actual", "➕ Nuevo Producto", "🕒 Historial de Movimientos"])

        # Consultas base para sedes
        res_sedes = supabase.table("sedes").select("id, nombre").execute()
        dict_sedes = {s['nombre']: s['id'] for s in res_sedes.data}

        # PESTAÑA 1: VISUALIZACIÓN Y REABASTECIMIENTO
        with tab1:
            st.subheader("Consulta de Existencias")
            # NUEVO: Filtro por ubicación para el Stock
            sede_filtro_nom = st.selectbox("📍 Filtrar por Ubicación/Sede", ["Todas"] + list(dict_sedes.keys()))
            
            query = supabase.table("inventario").select("*, sedes(nombre)").order("nombre_producto")
            if sede_filtro_nom != "Todas":
                query = query.eq("sede_id", dict_sedes[sede_filtro_nom])
            
            res_i = query.execute()

            if res_i.data:
                for p in res_i.data:
                    sede_p = p['sedes']['nombre'] if p.get('sedes') else "Sin asignar"
                    with st.expander(f"🛒 {p['nombre_producto']} | Ubicación: {sede_p} | Cantidad: {p['stock_actual']}"):
                        c1, c2 = st.columns([1, 2])
                        with c1: 
                            if p['foto_url']: st.image(p['foto_url'], width=150)
                            else: st.info("Sin imagen")
                        with c2:
                            st.write(f"**Precio:** ${p['precio_unitario']}")
                            with st.form(key=f"f_stock_{p['id']}"):
                                add = st.number_input("Cantidad que entra al almacén", min_value=0, step=1)
                                if st.form_submit_button("Actualizar Stock"):
                                    if add > 0:
                                        nuevo_total = p['stock_actual'] + add
                                        supabase.table("inventario").update({"stock_actual": nuevo_total}).eq("id", p['id']).execute()
                                        
                                        supabase.table("historial_inventario").insert({
                                            "producto_id": p['id'], 
                                            "usuario_id": st.session_state.usuario_id, 
                                            "cantidad_añadida": add,
                                            "sede_id": p['sede_id'] # Mantiene la relación de sede en el historial
                                        }).execute()
                                        st.success(f"Se añadieron {add} unidades")
                                        st.rerun()
            else:
                st.info("No hay productos registrados en esta ubicación.")

        # PESTAÑA 2: FORMULARIO DE NUEVO PRODUCTO
        with tab2:
            st.subheader("Registrar nuevo material en el catálogo")
            with st.form("form_nuevo_producto", clear_on_submit=True):
                nombre_p = st.text_input("Nombre del Producto")
                # NUEVO: Selección de sede obligatoria para el nuevo producto
                sede_p_nom = st.selectbox("Asignar a Sede/Ubicación", list(dict_sedes.keys()))
                desc_p = st.text_area("Descripción corta")
                
                c_p1, c_p2 = st.columns(2)
                precio_p = c_p1.number_input("Precio de Venta Unitario", min_value=0.0, step=0.5)
                stock_p = c_p2.number_input("Stock Inicial", min_value=0, step=1)
                
                foto_p = st.file_uploader("Subir foto del producto", type=["jpg", "png", "jpeg"])
                
                if st.form_submit_button("Guardar Producto"):
                    if nombre_p:
                        url_foto = subir_archivo(foto_p, "evidencias", "productos") if foto_p else None
                        
                        nuevo_prod = {
                            "nombre_producto": nombre_p,
                            "sede_id": dict_sedes[sede_p_nom], # Guardamos el ID de la sede
                            "descripcion": desc_p,
                            "precio_unitario": precio_p,
                            "stock_actual": stock_p,
                            "foto_url": url_foto
                        }
                        try:
                            supabase.table("inventario").insert(nuevo_prod).execute()
                            st.success(f"✅ {nombre_p} agregado a {sede_p_nom}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("El nombre del producto es obligatorio.")

        # PESTAÑA 3: HISTORIAL DE ENTRADAS
        with tab3:
            st.subheader("🕒 Log de Reabastecimientos")
            # NUEVO: Filtro de historial por sede
            sede_hist_nom = st.selectbox("Filtrar Historial por Sede", ["Todas"] + list(dict_sedes.keys()), key="h_sede")
            
            try:
                query_h = supabase.table("historial_inventario")\
                    .select("fecha_movimiento, cantidad_añadida, inventario(nombre_producto, sede_id), usuarios(nombre_usuario), sedes(nombre)")
                
                # Si se selecciona una sede, filtramos (necesitas que historial_inventario tenga sede_id o filtrar por la relación)
                res_h = query_h.order("fecha_movimiento", desc=True).execute()
                
                if res_h.data:
                    datos_tabla = []
                    for h in res_h.data:
                        # Filtrado manual si la sede está seleccionada
                        nombre_sede_h = h['sedes']['nombre'] if h.get('sedes') else "N/A"
                        
                        if sede_hist_nom == "Todas" or nombre_sede_h == sede_hist_nom:
                            datos_tabla.append({
                                "Fecha": pd.to_datetime(h['fecha_movimiento']).strftime('%d/%m/%Y %H:%M'),
                                "Producto": h['inventario']['nombre_producto'],
                                "Sede": nombre_sede_h,
                                "Cantidad": h['cantidad_añadida'],
                                "Encargado": h['usuarios']['nombre_usuario']
                            })
                    
                    if datos_tabla:
                        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay movimientos para la sede seleccionada.")
                else:
                    st.info("Aún no hay movimientos registrados.")
            except Exception as e:
                st.error(f"Error al cargar el historial: {e}")

# --- PÁGINA: NUEVA VENTA (CON DESCUENTOS Y DIRECCIÓN DETALLADA) ---
    elif menu == "Nueva Venta":
        st.title("🛒 Nueva Orden de Venta")
        
        # --- PASO 0: SELECCIÓN DE SEDE ORIGEN ---
        # Esto filtra todo el proceso
        res_sedes = supabase.table("sedes").select("id, nombre").eq("estatus", "Activa").execute()
        dict_sedes = {s['nombre']: s['id'] for s in res_sedes.data}
        
        col_sede_sel = st.columns(1)[0]
        sede_venta_nom = col_sede_sel.selectbox("📍 Seleccionar Tienda/Bodega de Despacho", list(dict_sedes.keys()))
        sede_id_seleccionada = dict_sedes[sede_venta_nom]

        col_selec, col_resumen = st.columns([1, 1])
        
        with col_selec:
            st.subheader("1. Selección de Materiales")
            # FILTRO: Solo productos de la sede seleccionada con stock > 0
            res_inv = supabase.table("inventario").select("*").eq("sede_id", sede_id_seleccionada).gt("stock_actual", 0).execute()
            
            if res_inv.data:
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
                
                if st.button("➕ Añadir a la Orden"):
                    if subtotal_item >= 0:
                        st.session_state.carrito.append({
                            "id": item_seleccionado['id'], 
                            "nombre": item_seleccionado['nombre_producto'], 
                            "precio_base": item_seleccionado['precio_unitario'], 
                            "cantidad": c_sel, 
                            "descuento": desc_sel,
                            "subtotal": subtotal_item,
                            "sede_id": sede_id_seleccionada # Guardamos referencia en el carrito
                        })
                        st.toast(f"Añadido: {item_seleccionado['nombre_producto']}")
            else:
                st.warning("⚠️ No hay productos con stock en esta ubicación.")

        with col_resumen:
            st.subheader("2. Resumen de la Orden")
            if st.session_state.carrito:
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[["nombre", "cantidad", "subtotal"]])
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
                nuevo_cli_tel = st.text_input("WhatsApp")
            
            fec_e = st.date_input("Fecha Programada")
        
        with c2:
            st.markdown("##### 📍 Dirección Detallada")
            calle = st.text_input("Calle y Número")
            colonia = st.text_input("Colonia")
            # REINTEGRADOS: Campos editables con valores por defecto
            municipio = st.text_input("Municipio/Delegación", value="Perote")
            estado = st.text_input("Estado", value="Veracruz")
            
            # Unimos la dirección completa dinámicamente
            lug_e_completo = f"{calle}, {colonia}, {municipio}, {estado}"
        
        with c3:
            st.markdown("##### 💰 Totales")
            flete = st.number_input("Flete ($)", min_value=0.0, step=50.0)
            maniobra = st.number_input("Maniobra ($)", min_value=0.0, step=50.0)
            pagado = st.number_input("Pago hoy ($)", min_value=0.0)
            
            total_v = float(subtotal_productos + flete + maniobra)
            credito = total_v - pagado
            st.markdown(f"### TOTAL: :green[${total_v:,.2f}]")
            evid = st.file_uploader("Evidencia de Pago", type=["jpg", "png", "pdf"])

        if st.button("✅ PROCESAR VENTA FINAL", use_container_width=True, type="primary"):
            if not st.session_state.carrito:
                st.error("Carrito vacío")
            elif not calle or not colonia:
                st.error("Faltan datos de dirección")
            else:
                target_id = None
                if c_final_sel == "-- AGREGAR CLIENTE NUEVO --":
                    res_new = supabase.table("Clientes").insert({"nombre": nuevo_cli_nom, "telefono": nuevo_cli_tel}).execute()
                    target_id = res_new.data[0]['id']
                else:
                    target_id = dict_cli[c_final_sel]

                url_e = subir_archivo(evid, "evidencias", "ventas") if evid else None
                
                # INSERT VENTA (Incluyendo la SEDE)
                v_ins = {
                    "cliente_id": target_id, 
                    "vendedor_id": st.session_state.usuario_id, 
                    "sede_id": sede_id_seleccionada, # REGISTRAMOS LA SEDE ORIGEN
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
                    # Insertar detalles
                    supabase.table("detalles_venta").insert({
                        "venta_id": id_v, "producto_id": art['id'], 
                        "cantidad": art['cantidad'], "precio_unitario": art['precio_base'], 
                        "descuento_aplicado": art['descuento'], "subtotal": art['subtotal']
                    }).execute()
                    
                    # Descontar stock (específico de esa sede)
                    s_act = supabase.table("inventario").select("stock_actual").eq("id", art['id']).single().execute().data['stock_actual']
                    supabase.table("inventario").update({"stock_actual": s_act - art['cantidad']}).eq("id", art['id']).execute()
                
                st.success(f"¡Venta registrada desde {sede_venta_nom}!")
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
                
                # --- BUSCADOR POR NOMBRE ---
                busqueda_c = st.text_input("🔍 Buscar cliente por nombre", "").lower()
                if busqueda_c:
                    df_c = df_c[df_c['nombre'].str.lower().str.contains(busqueda_c)]

                stats = []
                for _, c in df_c.iterrows():
                    cv = df_v[df_v['cliente_id'] == c['id']]
                    u_compra = pd.to_datetime(cv['fecha_venta'].max()).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not cv.empty else "N/A"
                    
                    stats.append({
                        "Nombre": c['nombre'], 
                        "Dirección": c.get('direccion', 'Sin dirección'),
                        "Saldo Deudor": cv['monto_credito'].sum() if not cv.empty else 0.0, 
                        "Total Compras": cv['monto_total'].sum() if not cv.empty else 0.0, 
                        "Última Compra": u_compra
                    })
                
                if stats:
                    df_final = pd.DataFrame(stats).sort_values("Saldo Deudor", ascending=False)
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                else:
                    st.info("No se encontraron clientes.")

            except Exception as e: 
                st.error(f"Error al cargar cartera: {e}")

        # --- TAB 2: EXPEDIENTE DETALLADO ---
        with tab2:
            st.subheader("Consulta de Historial por Cliente")
            res_c_exp = supabase.table("Clientes").select("*").order("nombre").execute()
            
            # --- FILTRO PARA EL SELECTBOX ---
            busqueda_exp = st.text_input("🔍 Filtrar cliente para auditar", "").lower()
            opciones_exp = [c for c in res_c_exp.data if busqueda_exp in c['nombre'].lower()]
            dict_c_exp = {c['nombre']: c for c in opciones_exp}
            
            if dict_c_exp:
                c_sel_nom = st.selectbox("Seleccionar Cliente", list(dict_c_exp.keys()))
                
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
                                col_info, col_btn = st.columns([4, 1])
                                with col_info:
                                    st.write(f"**Folio:** `{str(row['id'])[:8]}` | **Fecha:** {fecha_mx}")
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
            else:
                st.info("No se encontraron clientes.")

        # --- TAB 3: BUSCADOR GENERAL DE RECIBOS ---
        with tab3:
            st.subheader("Generación de Recibos")
            # --- BUSCADOR DE RECIBOS POR CLIENTE ---
            busqueda_rec = st.text_input("🔍 Buscar recibos por nombre de cliente", "").lower()
            
            res_rec = supabase.table("ventas").select("id, fecha_venta, monto_total, Clientes(nombre)").order("fecha_venta", desc=True).execute()
            
            recibos_filtrados = [r for r in res_rec.data if busqueda_rec in r['Clientes']['nombre'].lower()]
            
            for r in recibos_filtrados[:20]: # Limitamos a los últimos 20 encontrados
                fecha_mx = pd.to_datetime(r['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y')
                col_btn, col_info = st.columns([1, 4])
                with col_btn:
                    if st.button(f"Ver 📄", key=f"btn_list_{r['id']}"):
                        st.session_state.ver_id = r['id']
                        st.rerun()
                with col_info:
                    st.write(f"**{r['Clientes']['nombre']}** - ${r['monto_total']:,.2f} ({fecha_mx})")
            
            if not recibos_filtrados:
                st.info("No se encontraron recibos.")

    # --- LÓGICA DE VISUALIZACIÓN DEL RECIBO (GLOBAL) ---
    if 'ver_id' in st.session_state:
        st.divider()
        col_tit, col_close = st.columns([5, 1])
        with col_tit: st.subheader("🧾 Vista de Nota de Venta")
        with col_close: 
            if st.button("❌ Cerrar"):
                del st.session_state.ver_id
                st.rerun()
        
        # Consulta detallada
        vd = supabase.table("ventas").select("*, Clientes(*), usuarios(nombre_usuario)").eq("id", st.session_state.ver_id).single().execute().data
        items = supabase.table("detalles_venta").select("*, inventario(nombre_producto)").eq("venta_id", vd['id']).execute().data
        
        fecha_v_mx = pd.to_datetime(vd['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M')
        st.markdown(f"### CEDIS PEROTE")
        st.write(f"**Folio:** `{vd['id']}`")
        st.write(f"**Fecha:** {fecha_v_mx} | **Vendedor:** {vd['usuarios']['nombre_usuario']}")
        st.write(f"**Cliente:** {vd['Clientes']['nombre']} | **Entrega:** {vd['lugar_entrega']}")
        
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
        
        # 1. Consultamos todas las ventas (eliminamos el filtro .gt para no excluir nulos)
        res_v = supabase.table("ventas").select("id, monto_total, monto_credito, Clientes(nombre)").execute()
        
        if res_v.data:
            # 2. Filtramos manualmente para asegurar que aparezcan las que DEBEN dinero real
            ventas_con_deuda = []
            for v in res_v.data:
                # Calculamos saldo real: Monto Total - Abonos realizados
                res_a = supabase.table("abonos").select("monto_abono").eq("venta_id", v['id']).execute()
                total_abonado = sum(float(a['monto_abono']) for a in res_a.data)
                
                # Usamos monto_total como base para determinar la deuda actual
                monto_total = float(v.get('monto_total', 0))
                pago_inicial = monto_total - float(v.get('monto_credito', monto_total))
                saldo_actual = monto_total - (pago_inicial + total_abonado)
                
                if saldo_actual > 0:
                    # Actualizamos el valor de monto_credito temporalmente para que tu formulario funcione igual
                    v['monto_credito'] = saldo_actual
                    ventas_con_deuda.append(v)

            if ventas_con_deuda:
                # Diccionario para identificar la deuda seleccionada
                dict_d = {f"{v['Clientes']['nombre']} (Saldo Actual: ${v['monto_credito']:,.2f})": v for v in ventas_con_deuda}
                
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
                        # 1. La función ahora devuelve directamente la URL pública si tiene éxito
                        url_evidencia = subir_archivo(evid_abono, "evidencias", "abonos") if evid_abono else None
                        
                        # 2. Insertar el registro del abono
                        nuevo_abono = {
                            "venta_id": deuda_seleccionada['id'],
                            "vendedor_id": st.session_state.usuario_id,
                            "monto_abono": ab,
                            "forma_pago": forma_pago,
                            "evidencia_url": url_evidencia, # Se guardará como texto (https://...)
                            "referencia": referencia
                        }
                        
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
                            # Nota: nuevo_saldo se calcula sobre la deuda actual calculada
                            nuevo_saldo = deuda_seleccionada['monto_credito'] - ab
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

        # --- TAB 1: INVENTARIO DE UNIDADES ---
        with tab1:
            res_u = supabase.table("unidades").select("*").order("nombre_unidad").execute()
            res_c_total = supabase.table("combustible_unidades").select("costo_total").execute()
            df_u = pd.DataFrame(res_u.data)
            df_c_total = pd.DataFrame(res_c_total.data)

            if not df_u.empty:
                # Cálculos
                total_unidades = len(df_u)
                unidades_taller = len(df_u[df_u['estado'].str.contains("reparación", case=False, na=False)])
                gasto_mant = df_u['ultimo_costo_reparacion'].fillna(0).sum()
                gasto_gas = df_c_total['costo_total'].fillna(0).sum() if not df_c_total.empty else 0.0

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Unidades", total_unidades)
                c2.metric("En Taller", unidades_taller)
                c3.metric("Gasto Mant. Total", f"${gasto_mant:,.2f}")
                c4.metric("Gasto Gasolina Total", f"${gasto_gas:,.2f}")

                st.divider()
                
                for _, u in df_u.iterrows():
                    # Color dinámico según estado
                    emoji = "🟢" if u['estado'] == "activo" else "🟠" if u['estado'] == "en ruta" else "🔴"
                    with st.expander(f"{emoji} {u['nombre_unidad']} - {u['placas']} ({u['estado'].upper()})"):
                        col_img, col_info = st.columns([1, 2])
                        
                        with col_img:
                            if u.get('foto_unidad_url'):
                                st.image(u['foto_unidad_url'], use_container_width=True)
                            else: st.info("Sin fotografía.")

                        with col_info:
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Serie/VIN:** {u.get('serie', 'N/A')}")
                                st.write(f"**Color:** {u['color']}")
                                st.write(f"**Responsable:** {u['responsable_fijo']}")
                            with col_b:
                                st.write(f"**KM Actual:** {u.get('kilometraje_actual', 0):,} km")
                        
                        st.divider()
                        sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs(["🛠️ Mant.", "⛽ Comb.", "📦 Envíos", "📄 Docs"])
                        
                        with sub_t1:
                            res_hm = supabase.table("historial_unidades").select("*").eq("unidad_id", u['id']).order("fecha_ingreso", desc=True).execute()
                            if res_hm.data: st.dataframe(pd.DataFrame(res_hm.data)[['fecha_ingreso', 'costo_total', 'descripcion_falla']], use_container_width=True, hide_index=True)
                            else: st.info("Sin historial.")

                        with sub_t2:
                            res_hg = supabase.table("combustible_unidades").select("*").eq("unidad_id", u['id']).order("fecha", desc=True).execute()
                            if res_hg.data: st.dataframe(pd.DataFrame(res_hg.data)[['fecha', 'litros', 'costo_total']], use_container_width=True, hide_index=True)
                            else: st.info("Sin historial.")

                        with sub_t3:
                            res_he = supabase.table("envios").select("*, ventas(Clientes(nombre))").eq("unidad_id", u['id']).order("fecha_registro", desc=True).execute()
                            if res_he.data:
                                env_list = [{"Fecha": e['fecha_registro'][:10], "Cliente": e['ventas']['Clientes']['nombre'], "Estatus": e['estatus']} for e in res_he.data]
                                st.table(pd.DataFrame(env_list))
                            else: st.info("Sin envíos.")

                        with sub_t4:
                            d_col1, d_col2, d_col3 = st.columns(3)
                            for col, label, key in [(d_col1, "Seguro", "url_seguro"), (d_col2, "Tenencia", "url_tenencia"), (d_col3, "Verif.", "url_verificacion")]:
                                if u.get(key): col.link_button(f"Ver {label}", u[key], use_container_width=True)
                                else: col.warning(f"Sin {label}")
            else:
                st.warning("No hay unidades.")

# --- TAB 2: ALTA DE UNIDAD (ACTUALIZADA CON DOCUMENTOS) ---
            with tab2:
                st.subheader("Registrar Nueva Unidad")
                with st.form("f_nueva_unidad", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        n_u = st.text_input("Nombre de la Unidad")
                        p_u = st.text_input("Placas")
                        s_u = st.text_input("Número de Serie / VIN")
                        t_u = st.selectbox("Tipo", ["Torton", "Camioneta 3.5", "Pick-up", "Particular"])
                    with c2:
                        col_u = st.text_input("Color")
                        resp_u = st.text_input("Responsable Asignado")
                        km_u = st.number_input("Kilometraje Inicial", min_value=0)
                        foto_u = st.file_uploader("Fotografía de la Unidad", type=["jpg", "png"])
                    
                    st.markdown("---")
                    st.write("📂 **Cargar Documentación Inicial (PDF o Imagen)**")
                    cd1, cd2, cd3 = st.columns(3)
                    with cd1: f_seguro = st.file_uploader("Póliza de Seguro", type=["pdf", "jpg", "png"])
                    with cd2: f_tenencia = st.file_uploader("Comprobante Tenencia", type=["pdf", "jpg", "png"])
                    with cd3: f_verif = st.file_uploader("Verificación", type=["pdf", "jpg", "png"])

                    if st.form_submit_button("Guardar Unidad"):
                        # Subida de archivos
                        url_foto = subir_archivo(foto_u, "evidencias", "unidades") if foto_u else None
                        url_s = subir_archivo(f_seguro, "evidencias", "documentos") if f_seguro else None
                        url_t = subir_archivo(f_tenencia, "evidencias", "documentos") if f_tenencia else None
                        url_v = subir_archivo(f_verif, "evidencias", "documentos") if f_verif else None
                        
                        data_u = {
                            "nombre_unidad": n_u, "placas": p_u, "serie": s_u, "tipo": t_u, 
                            "color": col_u, "responsable_fijo": resp_u, "kilometraje_actual": km_u,
                            "foto_unidad_url": url_foto, "estado": "activo",
                            "url_seguro": url_s, "url_tenencia": url_t, "url_verificacion": url_v
                        }
                        supabase.table("unidades").insert(data_u).execute()
                        st.success("✅ Unidad y documentos registrados")
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

        # 1. Datos iniciales
        res_envios_finalizados = supabase.table("envios").select("venta_id").in_("estatus", ["terminado", "cancelado", "devuelto"]).execute()
        ids_excluir = [e['venta_id'] for e in res_envios_finalizados.data]

        # AJUSTE: Traemos el nombre de la sede desde la relación con ventas
        res_v_raw = supabase.table("ventas").select("*, Clientes(nombre), sedes(nombre)").order("fecha_entrega").execute()
        ventas_filtradas = [v for v in res_v_raw.data if v['id'] not in ids_excluir]
        
        res_unid = supabase.table("unidades").select("*").eq("estado", "activo").execute()
        res_oper = supabase.table("usuarios").select("id, nombre_usuario").execute()
        
        with tab_pend:
            st.subheader("Asignación y Despacho de Ruta")
            # AJUSTE: Mostramos la sede en la etiqueta de selección para saber de dónde sale el material
            ventas_opciones = {
                f"Folio: {v['id'][:8]} - {v['Clientes']['nombre']} (Sede: {v['sedes']['nombre'] if v['sedes'] else 'N/A'})": v 
                for v in ventas_filtradas
            }
            
            if ventas_opciones:
                v_sel_labels = st.multiselect("Ventas para la Ruta", list(ventas_opciones.keys()))
                if v_sel_labels:
                    with st.form("f_envio_multi"):
                        u_opts = {f"{u['nombre_unidad']} ({u['placas']})": u['id'] for u in res_unid.data}
                        u_envio = st.selectbox("Unidad", list(u_opts.keys()))
                        oper_opts = {o['nombre_usuario']: o['id'] for o in res_oper.data}
                        op_envio = st.selectbox("Operador Responsable", list(oper_opts.keys()))
                        acomp = st.text_input("Acompañantes")
                        estatus_ini = st.selectbox("Estatus Inicial", ["en preparacion", "listo para enviar", "enviado"])
                        
                        if st.form_submit_button("🚀 Confirmar Despacho"):
                            ruta_uuid = f"RUTA-{pd.Timestamp.now().strftime('%m%d-%H%M')}"
                            for l in v_sel_labels:
                                v_id = ventas_opciones[l]['id']
                                supabase.table("envios").insert({
                                    "venta_id": v_id, 
                                    "unidad_id": u_opts[u_envio], 
                                    "operador_id": oper_opts[op_envio],
                                    "acompanantes": acomp,
                                    "ruta_id": ruta_uuid, 
                                    "estatus": estatus_ini
                                }).execute()
                            
                            if estatus_ini == "enviado":
                                supabase.table("unidades").update({"estado": "en ruta"}).eq("id", u_opts[u_envio]).execute()
                            
                            st.success(f"Ruta {ruta_uuid} creada")
                            st.rerun()
            else:
                st.info("✅ No hay ventas pendientes.")

        # --- TAB 2: HISTORIAL Y SEGUIMIENTO DETALLADO ---
        with tab_hist:
            st.subheader("📋 Seguimiento de Rutas por Venta")
            busqueda = st.text_input("🔍 Buscar por Folio, Cliente o Sede", "").strip().lower()
            
            # AJUSTE: Agregamos sedes(nombre) en el select profundo
            res_env = supabase.table("envios").select("*, ventas(*, Clientes(*), sedes(*)), unidades(*), usuarios(*)").order("fecha_registro", desc=True).execute()
            
            envios_mostrar = res_env.data
            if busqueda:
                envios_mostrar = [
                    en for en in res_env.data 
                    if busqueda in en['ventas']['id'].lower() or 
                       busqueda in en['ventas']['Clientes']['nombre'].lower() or
                       (en['ventas']['sedes'] and busqueda in en['ventas']['sedes']['nombre'].lower())
                ]

            if envios_mostrar:
                for en in envios_mostrar:
                    cliente = en['ventas']['Clientes']['nombre']
                    # AJUSTE: Obtenemos el nombre de la sede de origen
                    sede_origen = en['ventas']['sedes']['nombre'] if en['ventas']['sedes'] else "N/A"
                    folio_v = en['ventas']['id'][:8]
                    estatus_actual = en['estatus'].upper()
                    label_ruta = f" | 🛣️ {en['ruta_id']}" if en.get('ruta_id') else ""
                    
                    # AJUSTE: Agregamos la sede al título del expander para visibilidad inmediata
                    with st.expander(f"🏢 {sede_origen} ➡️ 👤 {cliente} | Venta: {folio_v}{label_ruta} | [{estatus_actual}]"):
                        col_det, col_act = st.columns([2, 1])
                        
                        with col_det:
                            st.markdown(f"**Origen (Sede):** {sede_origen}") # Visualización clara del origen
                            st.markdown(f"**Unidad:** {en['unidades']['nombre_unidad']} ({en['unidades']['placas']})")
                            st.markdown(f"**Operador:** {en['usuarios']['nombre_usuario']}")
                            st.markdown(f"**Destino:** {en['ventas']['lugar_entrega']}")
                            
                            st.caption("🕒 Línea de tiempo de estatus:")
                            res_h = supabase.table("historial_estatus_envios").select("*").eq("envio_id", en['id']).order("fecha_cambio", desc=True).execute()
                            
                            if res_h.data:
                                for h in res_h.data:
                                    f_h = pd.to_datetime(h['fecha_cambio']).tz_convert('America/Mexico_City').strftime('%d/%m %H:%M')
                                    col_txt, col_btn = st.columns([0.8, 0.2])
                                    with col_txt:
                                        st.write(f"• `{f_h}`: **{h['estatus_nuevo'].upper()}**")
                                        if h.get('notas'): st.caption(f"💬 {h['notas']}")
                                    with col_btn:
                                        if h.get('evidencia_url'):
                                            st.link_button("📸 Ver", h['evidencia_url'], use_container_width=True)

                        with col_act:
                            st.markdown("##### Actualizar Estatus")
                            with st.form(f"f_upd_{en['id']}"):
                                opciones = ["en preparacion", "listo para enviar", "enviado", "retrasado", "recibido", "de regreso", "terminado", "cancelado", "devuelto"]
                                nuevo_est = st.selectbox("Nuevo Estado", opciones, index=opciones.index(en['estatus']) if en['estatus'] in opciones else 0)
                                nota_h = st.text_input("Nota del cambio", placeholder="Ej. Entregado")
                                evid_update = st.file_uploader("Adjuntar evidencia (Opcional)", type=["jpg", "png"], key=f"evid_{en['id']}")
                                
                                if st.form_submit_button("Actualizar 💾"):
                                    if nuevo_est != en['estatus'] or evid_update:
                                        url_evid = subir_archivo(evid_update, "evidencias", "envios") if evid_update else None
                                        
                                        upd_envio = {"estatus": nuevo_est}
                                        if url_evid:
                                            upd_envio["evidencia_salida_url"] = url_evid 
                                        if nuevo_est == "terminado":
                                            upd_envio["fecha_recepcion"] = str(pd.Timestamp.now(tz='America/Mexico_City'))
                                        
                                        supabase.table("envios").update(upd_envio).eq("id", en['id']).execute()

                                        supabase.table("historial_estatus_envios").insert({
                                            "envio_id": en['id'],
                                            "estatus_anterior": en['estatus'],
                                            "estatus_nuevo": nuevo_est,
                                            "usuario_id": st.session_state.usuario_id,
                                            "notas": nota_h,
                                            "evidencia_url": url_evid 
                                        }).execute()

                                        if nuevo_est in ["enviado", "retrasado", "de regreso", "recibido"]:
                                            supabase.table("unidades").update({"estado": "en ruta"}).eq("id", en['unidad_id']).execute()
                                        
                                        elif nuevo_est in ["terminado", "cancelado", "devuelto"]:
                                            ruta_id = en.get('ruta_id')
                                            liberar = True
                                            if ruta_id:
                                                res_r = supabase.table("envios").select("id, estatus").eq("ruta_id", ruta_id).execute()
                                                for item in res_r.data:
                                                    status_chk = nuevo_est if item['id'] == en['id'] else item['estatus']
                                                    if status_chk not in ["terminado", "cancelado", "devuelto"]:
                                                        liberar = False
                                                        break
                                            
                                            if liberar:
                                                supabase.table("unidades").update({"estado": "activo", "nota_estado": "Ruta finalizada"}).eq("id", en['unidad_id']).execute()
                                        
                                        st.success(f"Estatus actualizado")
                                        st.rerun()
            else:
                st.info("No hay registros de envíos.")
                    
    elif menu == "Gestión de Gastos":
        st.title("💰 Control de Gastos - CEDIS Perote")
        tab_reg, tab_hist = st.tabs(["➕ Registrar Gasto", "📜 Historial y Auditoría"])

        # Consultas base
        res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
        dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}
        
        res_u = supabase.table("unidades").select("id, nombre_unidad, placas, kilometraje_actual").order("nombre_unidad").execute()
        dict_unidades = {f"{u['nombre_unidad']} ({u['placas']})": u for u in res_u.data}

        # --- TAB 1: REGISTRO DE GASTOS ---
        with tab_reg:
            st.subheader("Nuevo Registro")
            
            # Sacamos los selectores del formulario para que sean interactivos
            c_top1, c_top2 = st.columns(2)
            with c_top1:
                t_gasto = st.selectbox("Tipo de Gasto", [
                    "Impuestos", "Salarios", "Compra de Mercancía", "Servicios (Luz/Agua)", 
                    "Mantenimiento", "Publicidad", "Herramientas", "Viáticos", "Renta","Combustible"
                ])
            with c_top2:
                responsable_nom = st.selectbox("Responsable del Gasto", list(dict_users.keys()))
                responsable_id = dict_users[responsable_nom]

            # SECCIÓN DINÁMICA: Aparece inmediatamente al elegir Combustible
            unidad_sel_id = None
            litros_g = 0.0
            km_g = 0
            
            if t_gasto == "Combustible":
                st.info("⛽ **Detalles de Combustible requeridos**")
                col_gas1, col_gas2, col_gas3 = st.columns(3)
                with col_gas1:
                    u_gas_nom = st.selectbox("Seleccionar Unidad", list(dict_unidades.keys()))
                    u_info = dict_unidades[u_gas_nom]
                    unidad_sel_id = u_info['id']
                with col_gas2:
                    litros_g = st.number_input("Litros cargados", min_value=0.0, step=1.0)
                with col_gas3:
                    km_min = int(u_info.get('kilometraje_actual', 0))
                    km_g = st.number_input("Kilometraje Actual", min_value=km_min, value=km_min)

            # Formulario para el resto de los datos y el botón de guardado
            with st.form("f_final_gasto", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    sub_g = st.selectbox("Clasificación Extra", [
                        "Gasto General", "Gasto por Comprobar", "Gasto Reembolsable", "Pago a Proveedor"
                    ])
                    monto_g = st.number_input("Monto Total ($)", min_value=0.0, step=100.0)
                
                with c2:
                    estatus_g = st.selectbox("Estado del Gasto", ["Pagado", "Pendiente", "En Revisión"])
                    evid_g = st.file_uploader("Evidencia (Ticket/Factura)", type=["jpg", "png", "pdf"])
                
                desc_g = st.text_area("Descripción del Gasto")

                if st.form_submit_button("💾 Guardar Gasto Completo"):
                    if monto_g <= 0:
                        st.error("El monto debe ser mayor a 0")
                    else:
                        url_g = subir_archivo(evid_g, "evidencias", "gastos") if evid_g else None
                        
                        # 1. Insertar en tabla GASTOS
                        ins_data = {
                            "usuario_id": responsable_id,
                            "tipo_gasto": t_gasto,
                            "subcategoria": sub_g,
                            "monto": monto_g,
                            "descripcion": desc_g,
                            "estatus_gasto": estatus_g,
                            "evidencia_url": url_g
                        }
                        supabase.table("gastos").insert(ins_data).execute()

                        # 2. Si es combustible, insertar en COMBUSTIBLE_UNIDADES
                        if t_gasto == "Combustible" and unidad_sel_id:
                            ppl = monto_g / litros_g if litros_g > 0 else 0
                            
                            data_comb = {
                                "unidad_id": unidad_sel_id,
                                "fecha": str(pd.Timestamp.now().date()),
                                "kilometraje_registro": int(km_g),
                                "litros": float(litros_g),
                                "costo_total": float(monto_g),
                                "precio_por_litro": float(ppl),
                                "ticket_url": url_g,
                                "vendedor_id": st.session_state.usuario_id
                            }
                            supabase.table("combustible_unidades").insert(data_comb).execute()
                            
                            # Actualizar KM en la unidad
                            supabase.table("unidades").update({"kilometraje_actual": km_g}).eq("id", unidad_sel_id).execute()
                            st.toast("⛽ Datos de flota actualizados")

                        st.success(f"✅ Gasto y vinculación registrados con éxito")
                        st.rerun()

            # --- TAB 2: HISTORIAL Y AUDITORÍA ---
            with tab_hist:
                st.subheader("Buscador de Gastos")
                res_gastos = supabase.table("gastos").select("*, usuarios(nombre_usuario)").order("fecha_registro", desc=True).execute()
                
                if res_gastos.data:
                    for g in res_gastos.data:
                        with st.expander(f"💰 {g['tipo_gasto']} - ${g['monto']:,.2f} ({g['fecha_registro'][:10]}) - {g['estatus_gasto']}"):
                            col_i, col_a = st.columns([2, 1])
                            
                            with col_i:
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
                                            "usuario_id": st.session_state.usuario_id,
                                            "comentario": nota_upd
                                        }).execute()
                                        
                                        supabase.table("gastos").update({"estatus_gasto": nuevo_est}).eq("id", g['id']).execute()
                                        st.rerun()
                else:
                    st.info("No hay gastos registrados.")
    
    elif menu == "Reportes":
        st.title("📊 Dashboard Operativo y Financiero")
        
        # --- CONSULTA DE SEDES PARA EL FILTRO ---
        res_s = supabase.table("sedes").select("id, nombre").execute()
        dict_sedes = {s['nombre']: s['id'] for s in res_s.data}
        
        # --- FILTRO DE FECHAS Y TIENDA ---
        st.subheader("Configuración del Reporte")
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        
        with col_f1:
            import datetime as dt_module
            today = dt_module.date.today()
            hace_un_mes = today - dt_module.timedelta(days=30)
            rango = st.date_input("Selecciona el rango", [hace_un_mes, today])
        
        with col_f2:
            opciones_filtro_sede = ["Todas"] + list(dict_sedes.keys())
            sede_sel_nom = st.selectbox("📍 Filtrar por Sede", opciones_filtro_sede)

        # Validamos que el usuario haya seleccionado ambas fechas
        if isinstance(rango, (list, tuple)) and len(rango) == 2:
            f_inicio, f_fin = rango
            f_ini_str = str(f_inicio)
            f_fin_str = str(f_fin)
            
            # --- CONSULTAS A SUPABASE (ACTUALIZADAS CON RELACIONES) ---
            # 1. Ventas + Clientes + Sedes
            q_v = supabase.table("ventas").select("*, Clientes(nombre), sedes(nombre)").gte("fecha_entrega", f_ini_str).lte("fecha_entrega", f_fin_str)
            if sede_sel_nom != "Todas":
                q_v = q_v.eq("sede_id", dict_sedes[sede_sel_nom])
            res_v = q_v.execute()
            df_v = pd.DataFrame(res_v.data)

            # 2. Gastos + Usuarios
            q_g = supabase.table("gastos").select("*, usuarios(nombre_usuario)").gte("fecha_registro", f_ini_str).lte("fecha_registro", f_fin_str)
            res_g = q_g.execute()
            df_g = pd.DataFrame(res_g.data)

            # 3. Mantenimiento y Combustible (Se mantienen igual)
            res_m = supabase.table("historial_unidades").select("id, costo_total").gte("fecha_ingreso", f_ini_str).lte("fecha_ingreso", f_fin_str).execute()
            df_m = pd.DataFrame(res_m.data)
            res_gas = supabase.table("combustible_unidades").select("id, costo_total").gte("fecha", f_ini_str).lte("fecha", f_fin_str).execute()
            df_gas = pd.DataFrame(res_gas.data)

            # --- PROCESAMIENTO DE DATOS ---
            if not df_v.empty: df_v = df_v.drop_duplicates(subset=['id'])
            if not df_g.empty: df_g = df_g.drop_duplicates(subset=['id'])
            if not df_m.empty: df_m = df_m.drop_duplicates(subset=['id'])
            if not df_gas.empty: df_gas = df_gas.drop_duplicates(subset=['id'])

            total_ingresos = pd.to_numeric(df_v['monto_total']).sum() if not df_v.empty else 0.0
            total_ventas_count = len(df_v)
            cartera_pendiente = pd.to_numeric(df_v['monto_credito']).sum() if not df_v.empty else 0.0

            if not df_g.empty:
                g_generales = pd.to_numeric(df_g[df_g['tipo_gasto'] != 'Combustible']['monto']).sum()
            else:
                g_generales = 0.0

            g_mantenimiento = pd.to_numeric(df_m['costo_total']).sum() if not df_m.empty else 0.0
            g_gasolina = pd.to_numeric(df_gas['costo_total']).sum() if not df_gas.empty else 0.0
            
            total_egresos = g_generales + g_mantenimiento + g_gasolina
            utilidad = total_ingresos - total_egresos - cartera_pendiente

            # --- SCORECARDS ---
            st.divider()
            st.write(f"### 📍 Reporte: {sede_sel_nom}")
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Ventas Totales", f"${total_ingresos:,.2f}")
            c2.metric("📦 Órdenes", f"{total_ventas_count}")
            c3.metric("💳 Cartera Pendiente", f"${cartera_pendiente:,.2f}", delta_color="inverse")

            c4, c5, c6 = st.columns(3)
            c4.metric("📉 Gasto Total", f"${total_egresos:,.2f}", delta_color="inverse")
            c5.metric("⚖️ Utilidad Neta", f"${utilidad:,.2f}")
            c6.metric("⛽ Gasolina", f"${g_gasolina:,.2f}")

            st.divider()
            
            # Gráfica de comparación
            if total_ingresos > 0 or total_egresos > 0:
                st.subheader("📊 Comparativo Ingresos vs Gastos")
                df_comp = pd.DataFrame({
                    "Concepto": ["Ventas Totales","Utilidad Neta", "Egresos"],
                    "Monto": [total_ingresos,utilidad, total_egresos]
                })
                st.bar_chart(df_comp.set_index("Concepto"))
            
            # --- NUEVA SECCIÓN: TABLAS DETALLADAS EN UNA FILA ---
            st.divider()
            st.subheader("📝 Detalle de Operaciones")
            col_t1, col_t2, col_t3 = st.columns(3)

            with col_t1:
                st.write("**🛒 Lista de Ventas**")
                if not df_v.empty:
                    df_v_tabla = pd.DataFrame([{
                        "Cliente": v['Clientes']['nombre'] if v.get('Clientes') else "N/A",
                        "Tienda": v['sedes']['nombre'] if v.get('sedes') else "N/A",
                        "Fecha": pd.to_datetime(v['fecha_entrega']).strftime('%d/%m/%Y'),
                        "Monto": f"${float(v['monto_total']):,.2f}"
                    } for _, v in df_v.iterrows()])
                    st.dataframe(df_v_tabla, use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin ventas en el periodo.")

            with col_t2:
                st.write("**💳 Cartera Pendiente**")
                df_p = df_v[df_v['monto_credito'].astype(float) > 0] if not df_v.empty else pd.DataFrame()
                if not df_p.empty:
                    df_p_tabla = pd.DataFrame([{
                        "Cliente": v['Clientes']['nombre'] if v.get('Clientes') else "N/A",
                        "Fecha Venta": pd.to_datetime(v['fecha_entrega']).strftime('%d/%m/%Y'),
                        "Deuda": f"${float(v['monto_credito']):,.2f}"
                    } for _, v in df_p.iterrows()])
                    st.dataframe(df_p_tabla, use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin deudas pendientes.")

            with col_t3:
                st.write("**📉 Listado de Gastos**")
                if not df_g.empty:
                    df_g_tabla = pd.DataFrame([{
                        "Fecha": pd.to_datetime(g['fecha_registro']).strftime('%d/%m/%Y'),
                        "Usuario": g['usuarios']['nombre_usuario'] if g.get('usuarios') else "N/A",
                        "Categoría": g['tipo_gasto'],
                        "Subcat": g['subcategoria'],
                        "Monto": f"${float(g['monto']):,.2f}"
                    } for _, g in df_g.iterrows()])
                    st.dataframe(df_g_tabla, use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin gastos en el periodo.")

        else:
            st.info("Por favor, selecciona el rango de fechas completo.")
                
    elif menu == "Gestión de Ventas":
        st.title("📊 Control Maestro de Ventas")

        try:
            # 1. Consulta con relaciones
            res_v = supabase.table("ventas").select("*, Clientes(nombre, telefono), sedes(nombre)").order("fecha_venta", desc=True).execute()
            df_v = pd.DataFrame(res_v.data)

            if not df_v.empty:
                # --- PRE-CÁLCULO DE ESTATUS REAL ---
                def calcular_estatus_real(row):
                    monto_total = float(row['monto_total'])
                    pago_inicial = monto_total - float(row.get('monto_credito', monto_total))
                    
                    # Traemos todos los abonos de esta venta para verificar estatus y montos
                    res_a = supabase.table("abonos").select("monto_abono, estatus_aprobacion").eq("venta_id", row['id']).execute()
                    abonos_data = res_a.data
                    
                    # Sumamos solo los que ya están aprobados
                    total_abonos_aprobados = sum(float(a['monto_abono']) for a in abonos_data if a['estatus_aprobacion'] == "aprobado")
                    
                    # Verificamos si existe CUALQUIER abono que aún esté pendiente
                    tiene_pendientes = any(a['estatus_aprobacion'] == "pendiente" for a in abonos_data)
                    
                    saldo_restante = monto_total - (pago_inicial + total_abonos_aprobados)
                    
                    # Condición: El saldo debe ser 0 Y no debe haber abonos pendientes de revisar
                    if saldo_restante <= 0 and not tiene_pendientes:
                        return "Pagado"
                    else:
                        return "Pendiente"

                df_v['estatus_real'] = df_v.apply(calcular_estatus_real, axis=1)
                df_v['nombre_cliente'] = df_v['Clientes'].apply(lambda x: x['nombre'] if x else "N/A")
                df_v['nombre_sede'] = df_v['sedes'].apply(lambda x: x['nombre'] if x else "N/A")

                # --- BUSCADOR Y FILTROS ---
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    busqueda = st.text_input("🔍 Buscar por Cliente o Folio", "").lower()
                with c2:
                    filtro_estatus = st.selectbox("Estado de Pago", ["Todos", "Pagado", "Pendiente"])
                with c3:
                    opciones_sedes = ["Todas"] + sorted(df_v['nombre_sede'].unique().tolist())
                    filtro_sede = st.selectbox("Filtrar por Sede", opciones_sedes)

                df_filtrado = df_v.copy()
                if busqueda:
                    df_filtrado = df_filtrado[df_filtrado['nombre_cliente'].str.lower().str.contains(busqueda) | df_filtrado['id'].str.contains(busqueda)]
                if filtro_estatus != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['estatus_real'] == filtro_estatus]
                if filtro_sede != "Todas":
                    df_filtrado = df_filtrado[df_filtrado['nombre_sede'] == filtro_sede]

                st.divider()

                # --- RENDERIZADO DE VENTAS FILTRADAS ---
                for _, v in df_filtrado.iterrows():
                    monto_total = float(v['monto_total'])
                    pago_inicial = monto_total - float(v.get('monto_credito', monto_total))
                    
                    res_a = supabase.table("abonos").select("*, usuarios(nombre_usuario)").eq("venta_id", v['id']).order("fecha_abono", desc=True).execute()
                    
                    total_abonado_aprobado = pago_inicial + sum(float(a['monto_abono']) for a in res_a.data if a['estatus_aprobacion'] == 'aprobado')
                    saldo_restante = monto_total - total_abonado_aprobado
                    
                    color_status = "green" if v['estatus_real'] == "Pagado" else "red"
                    label_status = v['estatus_real'].upper()

                    with st.expander(f"🧾 Folio: {v['id'][:8]} | {v['nombre_cliente']} | 📍 {v['nombre_sede']} | :{color_status}[{label_status}]"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**📅 Fecha:** {pd.to_datetime(v['fecha_venta']).strftime('%d/%m/%Y %H:%M')}")
                            st.markdown(f"**🏬 Sede de Despacho:** {v['nombre_sede']}")
                            st.markdown(f"**📍 Dirección de Entrega:** {v['lugar_entrega'] or 'No especificada'}")
                            st.markdown(f"**📞 Teléfono:** {v['Clientes']['telefono'] if v['Clientes'] else 'N/A'}")
                            
                            st.markdown("---")
                            st.caption("📦 Detalle de Materiales:")
                            res_det = supabase.table("detalles_venta").select("*, inventario(nombre_producto)").eq("venta_id", v['id']).execute()

                            if res_det.data:
                                df_det = pd.DataFrame(res_det.data)
                                df_det['Material'] = df_det['inventario'].apply(lambda x: x['nombre_producto'] if x else "N/A")
                                st.dataframe(df_det[['Material', 'cantidad', 'precio_unitario', 'descuento_aplicado', 'subtotal']], use_container_width=True, hide_index=True)
                            
                            st.markdown("---")
                            cargos = v.get('cargos_adicionales', {})
                            c_extra1, c_extra2, c_extra3 = st.columns(3)
                            with c_extra1: st.write(f"**Flete:** ${float(cargos.get('flete', 0)):,.2f}")
                            with c_extra2: st.write(f"**Maniobra:** ${float(cargos.get('maniobra', 0)):,.2f}")
                            with c_extra3: st.write(f"**Total Descuento:** -${df_det['descuento_aplicado'].sum() if res_det.data else 0:,.2f}")

                        with col2:
                            st.metric("Total Venta", f"${monto_total:,.2f}")
                            st.metric("Abonado (Aprobado)", f"${total_abonado_aprobado:,.2f}")
                            # Si el saldo es 0 pero hay pendientes, mostramos un aviso visual en el saldo
                            st.metric("Saldo Restante", f"${max(0, saldo_restante):,.2f}", delta=-total_abonado_aprobado, delta_color="inverse")
                            
                            if v['evidencia_url']:
                                st.link_button("Ver Comprobante Venta 📄", v['evidencia_url'])

                        if res_a.data or pago_inicial > 0:
                            st.markdown("📋 **Historial de Abonos:**")
                            for abono in res_a.data:
                                c_ab1, c_ab2, c_ab3 = st.columns([3, 2, 2])
                                with c_ab1:
                                    st.write(f"**{pd.to_datetime(abono['fecha_abono']).strftime('%d/%m/%Y %H:%M')}** - ${float(abono['monto_abono']):,.2f}")
                                    st.caption(f"Vendedor: {abono['usuarios']['nombre_usuario'] if abono['usuarios'] else 'N/A'}")
                                with c_ab2:
                                    status = abono.get('estatus_aprobacion', 'pendiente')
                                    color = "orange" if status == 'pendiente' else "green" if status == 'aprobado' else "red"
                                    st.markdown(f":{color}[{status.upper()}]")
                                with c_ab3:
                                    if status == 'pendiente':
                                        if st.button("Aprobar ✅", key=f"btn_aprobar_{abono['id']}"):
                                            supabase.table("abonos").update({"estatus_aprobacion": "aprobado", "aprobado_por": st.session_state.get('nombre_usuario', 'Administrador'), "fecha_revision": "now()"}).eq("id", abono['id']).execute()
                                            st.rerun()
                                    if abono['evidencia_url']:
                                        st.link_button("Ver 🖼️", abono['evidencia_url'])
                            st.divider()

            else:
                st.info("No se encontraron ventas.")
        except Exception as e:
            st.error(f"Error cargando gestión de ventas: {e}")
            
    elif menu == "Gestión de Sedes":
        st.title("📍 Gestión de Sedes y Ubicaciones - CEDIS Perote")
        tab_reg, tab_list, tab_hist = st.tabs(["➕ Registrar Sede", "🏢 Inventario de Sedes", "📜 Historial de Cambios"])

        # Consultas base
        res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
        dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}

        # --- TAB 1: REGISTRO DE SEDE ---
        with tab_reg:
            st.subheader("Dar de Alta Nueva Ubicación")
            with st.form("f_nueva_sede", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    n_sede = st.text_input("Nombre de la Sede", placeholder="Ej. Bodega Perote Centro")
                    t_sede = st.selectbox("Tipo de Sede", ["Tienda", "CEDIS", "Bodega", "Oficina", "Punto de Venta"])
                    dir_sede = st.text_input("Dirección Completa")
                    maps_url = st.text_input("URL de Google Maps", placeholder="https://goo.gl/maps/...")
                
                with c2:
                    resp_sede = st.selectbox("Responsable Asignado", list(dict_users.keys()))
                    estatus_ini = st.selectbox("Estatus Inicial", ["Activa", "En Reparación", "Cerrada Temporalmente", "En Construcción"])
                    horario = st.text_input("Horario de Operación", placeholder="Ej. Lunes a Viernes 9am - 6pm")
                    tel_sede = st.text_input("Teléfono de Contacto")

                desc_sede = st.text_area("Descripción y Notas Adicionales")
                
                st.markdown("---")
                st.write("📂 **Archivos y Documentación**")
                f1, f2, f3, f4 = st.columns(4)
                with f1: foto_s = st.file_uploader("Foto Principal", type=["jpg", "png"])
                with f2: doc_renta = st.file_uploader("Contrato Renta", type=["pdf", "jpg", "png"])
                with f3: doc_permiso = st.file_uploader("Permisos", type=["pdf", "jpg", "png"])
                with f4: doc_planos = st.file_uploader("Planos", type=["pdf", "jpg", "png"])

                if st.form_submit_button("📍 Guardar Sede"):
                    # Subida de archivos a la nueva carpeta 'sedes'
                    url_foto = subir_archivo(foto_s, "evidencias", "sedes") if foto_s else None
                    url_r = subir_archivo(doc_renta, "evidencias", "sedes") if doc_renta else None
                    url_p = subir_archivo(doc_permiso, "evidencias", "sedes") if doc_permiso else None
                    url_pl = subir_archivo(doc_planos, "evidencias", "sedes") if doc_planos else None

                    ins_sede = {
                        "nombre": n_sede,
                        "tipo_sede": t_sede,
                        "direccion_texto": dir_sede,
                        "google_maps_url": maps_url,
                        "responsable_id": dict_users[resp_sede],
                        "estatus": estatus_ini,
                        "horario_operacion": horario,
                        "telefono_contacto": tel_sede,
                        "descripcion": desc_sede,
                        "foto_url": url_foto,
                        "url_contrato_renta": url_r,
                        "url_permisos_municipales": url_p,
                        "url_planos": url_pl
                    }
                    supabase.table("sedes").insert(ins_sede).execute()
                    st.success(f"✅ Sede '{n_sede}' registrada correctamente.")
                    st.rerun()

        # --- TAB 2: INVENTARIO DE SEDES ---
        with tab_list:
            st.subheader("Listado de Ubicaciones")
            res_s = supabase.table("sedes").select("*, usuarios(nombre_usuario)").order("nombre").execute()
            
            if res_s.data:
                for s in res_s.data:
                    emoji = "🟢" if s['estatus'] == "Activa" else "🟠" if "Reparación" in s['estatus'] else "🔴"
                    with st.expander(f"{emoji} {s['nombre']} ({s['tipo_sede']}) - {s['estatus']}"):
                        col_i, col_d = st.columns([1, 2])
                        with col_i:
                            if s['foto_url']: st.image(s['foto_url'], use_container_width=True)
                            else: st.info("Sin foto.")
                        
                        with col_d:
                            st.write(f"**Responsable:** {s['usuarios']['nombre_usuario']}")
                            st.write(f"**Dirección:** {s['direccion_texto']}")
                            if s['google_maps_url']: st.link_button("🗺️ Abrir en Maps", s['google_maps_url'])
                            
                            st.markdown("---")
                            # Botones de documentos
                            d1, d2, d3 = st.columns(3)
                            if s['url_contrato_renta']: d1.link_button("📄 Contrato", s['url_contrato_renta'], use_container_width=True)
                            if s['url_permisos_municipales']: d2.link_button("📜 Permisos", s['url_permisos_municipales'], use_container_width=True)
                            if s['url_planos']: d3.link_button("📐 Planos", s['url_planos'], use_container_width=True)

                        # Actualización de Estatus
                        st.markdown("---")
                        with st.form(f"f_upd_sede_{s['id']}"):
                            st.write("🔄 **Actualizar Estado de la Sede**")
                            c_u1, c_u2 = st.columns(2)
                            nuevo_est = c_u1.selectbox("Nuevo Estatus", ["Activa", "En Reparación", "Cerrada Temporalmente", "En Construcción"], key=f"est_{s['id']}")
                            motivo_c = c_u2.text_input("Motivo del cambio", key=f"mot_{s['id']}")
                            
                            if st.form_submit_button("Actualizar Estatus"):
                                if nuevo_est != s['estatus']:
                                    # 1. Historial
                                    supabase.table("historial_estatus_sedes").insert({
                                        "sede_id": s['id'],
                                        "estatus_anterior": s['estatus'],
                                        "estatus_nuevo": nuevo_est,
                                        "motivo": motivo_c,
                                        "usuario_id": st.session_state.usuario_id
                                    }).execute()
                                    # 2. Update Sede
                                    supabase.table("sedes").update({"estatus": nuevo_est}).eq("id", s['id']).execute()
                                    st.success("Estatus actualizado")
                                    st.rerun()

        # --- TAB 3: HISTORIAL DE CAMBIOS ---
        with tab_hist:
            st.subheader("📜 Auditoría de Movimientos")
            res_h = supabase.table("historial_estatus_sedes").select("*, sedes(nombre), usuarios(nombre_usuario)").order("fecha_cambio", desc=True).execute()
            
            if res_h.data:
                df_h = pd.DataFrame([{
                    "Fecha": pd.to_datetime(h['fecha_cambio']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M'),
                    "Sede": h['sedes']['nombre'],
                    "Estado Anterior": h['estatus_anterior'],
                    "Estado Nuevo": h['estatus_nuevo'],
                    "Motivo": h['motivo'],
                    "Usuario": h['usuarios']['nombre_usuario']
                } for h in res_h.data])
                st.table(df_h)
            else:
                st.info("No hay cambios registrados en el historial.")
