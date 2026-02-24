import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
from fpdf import FPDF
import urllib.parse

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CEDIS Perote - Control de Materiales", layout="wide", page_icon="🏗️")

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

    # --- DISEÑO DEL SIDEBAR ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1532/1532692.png", width=100) # Opcional: logo
    st.sidebar.title("📌 CEDIS Perote")
    st.sidebar.markdown(f"**Bienvenido,** {nombre} \n*Rol: {rol.capitalize()}*")
    st.sidebar.divider()

    # --- CONTROL DE ACCESO POR ROL ---
    # Definimos qué menús ve cada rol
    menu_roles = {
        "admin": [
            "Inicio", "Inventario", "Nueva Venta", "Registrar Abono", "Clientes", 
            "Logística y Envíos", "Flota y Unidades", "Gestión de Gastos", 
            "Gestión de Ventas", "Gestión de Sedes", "Registro de Clientes", "Reportes"
        ],
        "dev": [
            "Inicio", "Inventario", "Nueva Venta", "Registrar Abono", "Clientes", 
            "Logística y Envíos", "Flota y Unidades", "Gestión de Gastos", 
            "Gestión de Ventas", "Gestión de Sedes", "Registro de Clientes", "Reportes"
        ],
        "ventas": [
            "Inventario", "Nueva Venta", "Registrar Abono", "Clientes", "Registro de Clientes"
        ],
        "admin_ventas": [
            "Inventario", "Nueva Venta", "Registrar Abono", "Clientes", "Registro de Clientes"
        ],
        "logistica": [
            "Logística y Envíos", "Flota y Unidades", "Inventario"
        ],
        "gastos": [
            "Gestión de Gastos", "Inicio"
        ]
    }

    # --- CONFIGURACIÓN DE PERMISOS PARA TABS DENTRO DE CADA MENÚ ---
    permisos_tabs = {
        "admin": {
            "Inventario": ["📋 Stock Actual", "➕ Nuevo Producto", "🕒 Historial", "✏️ Editar Producto"],
            "Flota y Unidades": ["📋 Inventario", "➕ Alta de Unidad", "🛠️ Mantenimiento", "⛽ Combustible"],
            "Gestión de Gastos": ["➕ Registrar Gasto", "📜 Historial y Auditoría"],
            "Clientes": ["📊 Cartera General", "🔍 Expediente Detallado", "🧾 Ver Recibos"],
            "Logística y Envíos": ["📦 Envíos Pendientes", "📜 Historial de Rutas"],
            "Gestión de Sedes": ["➕ Registrar Sede", "🏢 Inventario de Sedes", "📜 Historial de Cambios"]
        },
        "dev": {
            "Inventario": ["📋 Stock Actual", "➕ Nuevo Producto", "🕒 Historial", "✏️ Editar Producto"],
            "Flota y Unidades": ["📋 Inventario", "➕ Alta de Unidad", "🛠️ Mantenimiento", "⛽ Combustible"],
            "Gestión de Gastos": ["➕ Registrar Gasto", "📜 Historial y Auditoría"],
            "Clientes": ["📊 Cartera General", "🔍 Expediente Detallado", "🧾 Ver Recibos"],
            "Logística y Envíos": ["📦 Envíos Pendientes", "📜 Historial de Rutas"],
            "Gestión de Sedes": ["➕ Registrar Sede", "🏢 Inventario de Sedes", "📜 Historial de Cambios"]
        },
        "ventas": {
            "Inventario": ["📋 Stock Actual"],  # Vendedor solo ve stock actual
            "Clientes": ["📊 Cartera General", "🧾 Ver Recibos"],  # No ve expediente detallado
            "Logística y Envíos": [],  # No ve nada de logística
            "Flota y Unidades": [],  # No ve flota
            "Gestión de Gastos": [],  # No ve gastos
            "Gestión de Sedes": []  # No ve sedes
        },
        "admin_ventas": {
            "Inventario": ["📋 Stock Actual","➕ Nuevo Producto","✏️ Editar Producto"],  # Vendedor solo ve stock actual
            "Clientes": ["📊 Cartera General", "🧾 Ver Recibos"],  # No ve expediente detallado
            "Logística y Envíos": [],  # No ve nada de logística
            "Flota y Unidades": [],  # No ve flota
            "Gestión de Gastos": [],  # No ve gastos
            "Gestión de Sedes": []  # No ve sedes
        },
        "logistica": {
            "Inventario": ["📋 Stock Actual"],  # Logística solo ve stock actual
            "Flota y Unidades": ["📋 Inventario", "🛠️ Mantenimiento", "⛽ Combustible"],  # Ve inventario y combustible
            "Logística y Envíos": ["📦 Envíos Pendientes", "📜 Historial de Rutas"],  # Ve todo
            "Gestión de Gastos": [],  # No ve gastos
            "Clientes": [],  # No ve clientes
            "Gestión de Sedes": []  # No ve sedes
        },
        "gastos": {
            "Gestión de Gastos": ["➕ Registrar Gasto", "📜 Historial y Auditoría"],  # Ve todo
            "Inventario": [],  # No ve inventario
            "Flota y Unidades": [],  # No ve flota
            "Clientes": [],  # No ve clientes
            "Logística y Envíos": [],  # No ve logística
            "Gestión de Sedes": []  # No ve sedes
        }
    }

    # Función para filtrar tabs por rol
    def filtrar_tabs_por_rol(rol, menu_actual, tabs_disponibles):
        """
        Filtra las tabs disponibles según el rol del usuario y el menú actual.
        Retorna las tabs permitidas o todas si no hay configuración específica.
        """
        # Si el rol no existe en permisos_tabs, devolvemos todas las tabs
        if rol not in permisos_tabs:
            return tabs_disponibles
        
        permisos_menu = permisos_tabs[rol].get(menu_actual, None)
        
        # Si no hay configuración específica para este menú, mostramos todas las tabs
        if permisos_menu is None:
            return tabs_disponibles
        
        # Si la lista está vacía, no muestra ninguna tab
        if len(permisos_menu) == 0:
            return []
        
        # Filtramos las tabs permitidas
        tabs_permitidas = []
        for tab in tabs_disponibles:
            if any(tab_text in tab for tab_text in permisos_menu):
                tabs_permitidas.append(tab)
        
        return tabs_permitidas

    # Obtenemos las opciones para el rol actual (si el rol no existe, ve un menú básico)
    opciones = menu_roles.get(rol, ["Inventario"])
    
    # Menú con mejor presentación
    menu = st.sidebar.selectbox("📂 Navegación", opciones)
    
    st.sidebar.divider()
    if st.sidebar.button("🔓 Cerrar Sesión", use_container_width=True):
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
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["📋 Stock Actual", "➕ Nuevo Producto", "🕒 Historial", "✏️ Editar Producto"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Inventario", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Inventario.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)
            
            res_sedes = supabase.table("sedes").select("id, nombre").execute()
            dict_sedes = {s['nombre']: s['id'] for s in res_sedes.data}
            
            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Stock Actual" in tab_name:
                        st.subheader("Consulta de Existencias")
                        c1, c2 = st.columns(2)
                        sede_filtro_nom = c1.selectbox("📍 Filtrar por Ubicación", ["Todas"] + list(dict_sedes.keys()))
                        busqueda_p = c2.text_input("🔍 Buscar por nombre de producto", "").lower()
                        
                        query = supabase.table("inventario").select("*, sedes(nombre)").order("nombre_producto")
                        if sede_filtro_nom != "Todas":
                            query = query.eq("sede_id", dict_sedes[sede_filtro_nom])
                        
                        res_i = query.execute()
                        
                        if res_i.data:
                            productos_filtrados = [p for p in res_i.data if busqueda_p in p['nombre_producto'].lower()]
                            
                            for p in productos_filtrados:
                                sede_p = p['sedes']['nombre'] if p.get('sedes') else "Sin asignar"
                                label_granel = " (Granel)" if p.get('es_granel') else ""
                                with st.expander(f"🛒 {p['nombre_producto']} | {p['stock_actual']} {p.get('unidad_medida', 'unidades')} | {sede_p}{label_granel}"):
                                    c1, c2 = st.columns([1, 2])
                                    with c1: 
                                        if p['foto_url']: st.image(p['foto_url'], width=150)
                                        else: st.info("Sin imagen")
                                    with c2:
                                        st.write(f"**Precio Venta:** ${p['precio_unitario']} | **Costo Compra:** ${p.get('precio_compra', 0)}")
                                        if p.get('es_granel'):
                                            st.write(f"**Costo Tonelada:** ${p.get('costo_tonelada', 0):,.2f}")
                                        
                                        with st.form(key=f"f_stock_{p['id']}"):
                                            add = st.number_input(f"Cantidad en {p.get('unidad_medida', 'unidades')}", min_value=0.0, step=0.1 if p.get('es_granel') else 1.0)
                                            if st.form_submit_button("Actualizar Stock"):
                                                if add > 0:
                                                    nuevo_total = float(p['stock_actual']) + float(add)
                                                    supabase.table("inventario").update({"stock_actual": nuevo_total}).eq("id", p['id']).execute()
                                                    supabase.table("historial_inventario").insert({
                                                        "producto_id": p['id'], "usuario_id": st.session_state.usuario_id, 
                                                        "cantidad_añadida": add, "sede_id": p['sede_id']
                                                    }).execute()
                                                    st.success("Stock actualizado")
                                                    st.rerun()
                        else:
                            st.info("No hay productos registrados.")
                    
                    elif "Nuevo Producto" in tab_name:
                        st.subheader("Registrar nuevo material")
                        with st.form("form_nuevo_producto", clear_on_submit=True):
                            nombre_p = st.text_input("Nombre del Producto")
                            sede_p_nom = st.selectbox("Asignar a Sede/Ubicación", list(dict_sedes.keys()))
                            desc_p = st.text_area("Descripción corta")
                            
                            c1, c2, c3 = st.columns(3)
                            unidad_p = c1.selectbox("Unidad de Medida", ["Pza", "Kg", "Bulto", "M3", "Tramo"])
                            es_granel = c2.checkbox("¿Es producto a granel?")
                            costo_ton = c3.number_input("Costo por Tonelada", min_value=0.0)
                            
                            c_p1, c_p2, c_p3 = st.columns(3)
                            precio_p = c_p1.number_input("Precio Venta", min_value=0.0)
                            costo_p = c_p2.number_input("Precio Compra (Costo)", min_value=0.0)
                            stock_p = c_p3.number_input("Stock Inicial", min_value=0.0)
                            
                            foto_p = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])
                            
                            if st.form_submit_button("Guardar Producto"):
                                if nombre_p:
                                    url_foto = subir_archivo(foto_p, "evidencias", "productos") if foto_p else None
                                    nuevo_prod = {
                                        "nombre_producto": nombre_p, "sede_id": dict_sedes[sede_p_nom],
                                        "descripcion": desc_p, "precio_unitario": float(precio_p),
                                        "precio_compra": float(costo_p), "stock_actual": float(stock_p),
                                        "foto_url": url_foto, "unidad_medida": unidad_p,
                                        "es_granel": es_granel, "costo_tonelada": float(costo_ton) if es_granel else 0.0
                                    }
                                    supabase.table("inventario").insert(nuevo_prod).execute()
                                    st.success("Guardado")
                                    st.rerun()
                    
                    elif "Historial" in tab_name:
                        st.subheader("🕒 Log de Reabastecimientos")
                        c1, c2 = st.columns(2)
                        sede_h = c1.selectbox("Filtrar por Sede", ["Todas"] + list(dict_sedes.keys()), key="h_sede")
                        busqueda_h = c2.text_input("🔍 Buscar producto en historial", "")
                        
                        res_h = supabase.table("historial_inventario").select("*, inventario(nombre_producto, sede_id), usuarios(nombre_usuario), sedes(nombre)").order("fecha_movimiento", desc=True).execute()
                        
                        if res_h.data:
                            datos_tabla = []
                            for h in res_h.data:
                                nom_sede = h['sedes']['nombre'] if h.get('sedes') else "N/A"
                                nom_prod = h['inventario']['nombre_producto'] if h.get('inventario') else "N/A"
                                if (sede_h == "Todas" or nom_sede == sede_h) and (busqueda_h.lower() in nom_prod.lower()):
                                    datos_tabla.append({
                                        "Fecha": pd.to_datetime(h['fecha_movimiento']).strftime('%d/%m/%Y %H:%M'),
                                        "Producto": nom_prod, "Sede": nom_sede,
                                        "Cantidad": h['cantidad_añadida'], "Encargado": h['usuarios']['nombre_usuario']
                                    })
                            st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
                    
                    elif "Editar Producto" in tab_name:
                        st.subheader("✏️ Modificar Detalles del Producto")
                        sede_edit_nom = st.selectbox("1. Seleccionar Sede", list(dict_sedes.keys()), key="edit_sede_sel")
                        
                        res_edit = supabase.table("inventario").select("*").eq("sede_id", dict_sedes[sede_edit_nom]).order("nombre_producto").execute()
                        
                        if res_edit.data:
                            dict_edit = {p['nombre_producto']: p for p in res_edit.data}
                            busqueda_edit = st.text_input("🔍 Buscar producto para editar", "")
                            opciones_edit = [n for n in dict_edit.keys() if busqueda_edit.lower() in n.lower()]
                            
                            if opciones_edit:
                                p_edit_nom = st.selectbox("2. Seleccionar Producto", opciones_edit)
                                p_data = dict_edit[p_edit_nom]
                                
                                with st.form("form_edit_prod"):
                                    new_nom = st.text_input("Nombre", value=p_data['nombre_producto'])
                                    new_desc = st.text_area("Descripción", value=p_data.get('descripcion', ''))
                                    
                                    col_e1, col_e2, col_e3 = st.columns(3)
                                    new_precio = col_e1.number_input("Precio Venta", value=float(p_data['precio_unitario']))
                                    new_costo = col_e2.number_input("Precio Compra", value=float(p_data.get('precio_compra', 0)))
                                    new_unidad = col_e3.selectbox("Unidad", ["Pza", "Kg", "Bulto", "M3", "Tramo"], index=["Pza", "Kg", "Bulto", "M3", "Tramo"].index(p_data.get('unidad_medida', 'Pza')))
                                    
                                    col_e4, col_e5 = st.columns(2)
                                    new_granel = col_e4.checkbox("Es granel", value=p_data.get('es_granel', False))
                                    new_costo_ton = col_e5.number_input("Costo Tonelada", value=float(p_data.get('costo_tonelada', 0)))
                                    
                                    if st.form_submit_button("Actualizar Información"):
                                        upd = {
                                            "nombre_producto": new_nom, "descripcion": new_desc,
                                            "precio_unitario": new_precio, "precio_compra": new_costo,
                                            "unidad_medida": new_unidad, "es_granel": new_granel,
                                            "costo_tonelada": new_costo_ton
                                        }
                                        supabase.table("inventario").update(upd).eq("id", p_data['id']).execute()
                                        st.success("Producto actualizado correctamente")
                                        st.rerun()
                            else:
                                st.warning("No se encontraron productos con ese nombre.")
                        else:
                            st.info("No hay productos en esta sede.")

# --- PÁGINA: NUEVA VENTA (CON DESCUENTOS Y DIRECCIÓN DETALLADA) ---
    elif menu == "Nueva Venta":
        st.title("🛒 Nueva Orden de Venta")
        from fpdf import FPDF 

        # --- PASO 0: SELECCIÓN DE SEDE ORIGEN ---
        res_sedes = supabase.table("sedes").select("id, nombre").eq("estatus", "Activa").execute()
        dict_sedes = {s['nombre']: s['id'] for s in res_sedes.data}
        
        col_sede_sel = st.columns(1)[0]
        sede_venta_nom = col_sede_sel.selectbox("📍 Seleccionar Tienda/Bodega de Despacho", list(dict_sedes.keys()))
        sede_id_seleccionada = dict_sedes[sede_venta_nom]

        col_selec, col_resumen = st.columns([1, 1])
        
        with col_selec:
            st.subheader("1. Selección de Materiales")
            res_inv = supabase.table("inventario").select("*")\
                .eq("sede_id", sede_id_seleccionada)\
                .or_("stock_actual.gt.0,es_granel.eq.true")\
                .execute()
            
            if res_inv.data:
                dict_inv = {
                    f"{i['nombre_producto']} (Stock: {i['stock_actual']} {i.get('unidad_medida', 'Pza')})": i 
                    for i in res_inv.data
                }
                
                opciones_prod = list(dict_inv.keys())
                p_sel_label = st.selectbox("Producto/Material", opciones_prod)
                item_seleccionado = dict_inv[p_sel_label]
                
                es_granel = item_seleccionado.get('es_granel', False)
                unidad = item_seleccionado.get('unidad_medida', 'Pza')
                precio_lista = float(item_seleccionado['precio_unitario'])

                c_input1, c_input2 = st.columns(2)
                with c_input1:
                    if es_granel:
                        c_sel = st.number_input(f"Cantidad en {unidad}", min_value=0.01, value=1.0, step=0.1)
                    else:
                        c_sel = st.number_input(f"Cantidad ({unidad})", min_value=1, max_value=int(item_seleccionado['stock_actual']), value=1)
                
                with c_input2:
                    precio_venta_final = st.number_input(f"Precio por {unidad} ($)", min_value=0.0, value=precio_lista, step=10.0)
                
                diferencia_unitario = precio_lista - precio_venta_final
                desc_total_auto = diferencia_unitario * float(c_sel) if diferencia_unitario > 0 else 0.0
                
                precio_bruto = precio_lista * float(c_sel)
                subtotal_item = precio_venta_final * float(c_sel)
                
                if diferencia_unitario > 0:
                    st.caption(f"Precio Original: ${precio_bruto:,.2f} | Descuento: -${desc_total_auto:,.2f}")
                
                st.write(f"**Subtotal Final: :green[${subtotal_item:,.2f}]**")
                
                if st.button("➕ Añadir a la Orden"):
                    if subtotal_item >= 0:
                        st.session_state.carrito.append({
                            "id": item_seleccionado['id'], 
                            "nombre": item_seleccionado['nombre_producto'], 
                            "precio_base": precio_lista,
                            "cantidad": c_sel, 
                            "descuento": desc_total_auto,
                            "subtotal": subtotal_item,
                            "sede_id": sede_id_seleccionada,
                            "unidad": unidad
                        })
                        st.toast(f"Añadido: {item_seleccionado['nombre_producto']}")
            else:
                st.warning("⚠️ No hay productos disponibles en esta ubicación.")

        with col_resumen:
            st.subheader("2. Resumen de la Orden")
            if st.session_state.carrito:
                df_car = pd.DataFrame(st.session_state.carrito)
                df_car['Cant. Detalle'] = df_car.apply(lambda x: f"{x['cantidad']} {x['unidad']}", axis=1)
                st.table(df_car[["nombre", "Cant. Detalle", "subtotal"]])
                
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
            tipo_v = st.selectbox("Tipo de Venta", ["Publico", "Reventa"])

        with c2:
            st.markdown("##### 📍 Dirección Detallada")
            n_remision = st.number_input("N° de Remisión (Foliado Nota)", min_value=0, step=1, value=0)
            calle = st.text_input("Calle y Número")
            colonia = st.text_input("Colonia")
            cp = st.text_input("Código Postal (CP)", placeholder="Ej: 91270")
            municipio = st.text_input("Municipio/Delegación", value="Perote")
            estado = st.text_input("Estado", value="Veracruz")
            lug_e_completo = f"{calle}, {colonia}, CP: {cp}, {municipio}, {estado}"

            if cp:
                query_maps = f"{sede_venta_nom} a CP {cp}, {municipio}, {estado}"
                url_maps = f"https://www.google.com/maps/dir/{sede_venta_nom}/{cp}+{municipio}"
                st.link_button("🗺️ Abrir Maps para calcular Distancia", url_maps, use_container_width=True)

            st.markdown("---")
            st.info("⛽ **Calculadora de Flete**")
            km_ida = st.number_input("Distancia de ida (Km)", min_value=0.0, step=0.1)
            costo_casetas = st.number_input("Casetas Ida y Vuelta ($)", min_value=0.0, step=10.0)
            
            dist_total = (km_ida * 2) + 20
            gasolina_est = (dist_total / 1.7) * 26.60
            pago_op = dist_total * 2.8
            ganancia_fix = 1000.0
            
            flete_sugerido = gasolina_est + pago_op + costo_casetas + ganancia_fix
            st.caption(f"Flete Sugerido: ${flete_sugerido:,.2f}")
            st.caption(f"Cantidad A Agregar Por Unidad: ${flete_sugerido/c_sel:,.2f}")
            st.caption(f"Nuevo Precio Por Unidad: ${(flete_sugerido/c_sel)+precio_lista:,.2f}")

        with c3:
            st.markdown("##### 💰 Totales")
            flete = st.number_input("Flete Final ($)", min_value=0.0, value=float(flete_sugerido), step=50.0)
            maniobra = st.number_input("Maniobra ($)", min_value=0.0, step=50.0)
            
            subtotal_base = float(subtotal_productos + flete + maniobra)
            aplicar_iva = st.toggle("Añadir IVA (16%)")
            iva_monto = subtotal_base * 0.16 if aplicar_iva else 0.0
            
            total_v = subtotal_base + iva_monto
            pagado = st.number_input("Pago hoy ($)", min_value=0.0)
            credito = total_v - pagado
            
            st.markdown(f"### TOTAL: :green[${total_v:,.2f}]")
            notas_venta = st.text_area("Notas de la Venta (para el PDF)")
            evid = st.file_uploader("Evidencia de Pago", type=["jpg", "png", "pdf"])

        col_btns_1, col_btns_2 = st.columns(2)
        
        with col_btns_1:
            if st.button("✅ PROCESAR VENTA FINAL", use_container_width=True, type="primary"):
                if not st.session_state.carrito:
                    st.error("Carrito vacío")
                elif not calle or not cp:
                    st.error("Faltan datos de dirección para concretar venta")
                else:
                    target_id = None
                    nombre_cliente = nuevo_cli_nom if c_final_sel == "-- AGREGAR CLIENTE NUEVO --" else c_final_sel
                    
                    if c_final_sel == "-- AGREGAR CLIENTE NUEVO --":
                        res_new = supabase.table("Clientes").insert({"nombre": nuevo_cli_nom, "telefono": nuevo_cli_tel}).execute()
                        target_id = res_new.data[0]['id']
                    else:
                        target_id = dict_cli[c_final_sel]

                    # Generar PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(200, 10, txt="NOTA DE VENTA", ln=True, align='C')
                    pdf.set_font("Arial", "", 12)
                    pdf.ln(10)
                    pdf.cell(200, 10, txt=f"Cliente: {nombre_cliente}", ln=True)
                    pdf.cell(200, 10, txt=f"Fecha: {fec_e} | Remisión: {n_remision}", ln=True)
                    pdf.cell(200, 10, txt=f"Tipo: {tipo_v}", ln=True)
                    pdf.ln(5)
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(100, 10, txt="Producto", border=1)
                    pdf.cell(40, 10, txt="Cant.", border=1)
                    pdf.cell(40, 10, txt="Subtotal", border=1, ln=True)
                    pdf.set_font("Arial", "", 12)
                    for item in st.session_state.carrito:
                        pdf.cell(100, 10, txt=str(item['nombre']), border=1)
                        pdf.cell(40, 10, txt=f"{item['cantidad']} {item['unidad']}", border=1)
                        pdf.cell(40, 10, txt=f"${item['subtotal']:,.2f}", border=1, ln=True)
                    pdf.ln(5)
                    pdf.cell(200, 10, txt=f"Flete: ${flete:,.2f} | Maniobra: ${maniobra:,.2f}", ln=True)
                    if aplicar_iva: pdf.cell(200, 10, txt=f"IVA (16%): ${iva_monto:,.2f}", ln=True)
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(200, 10, txt=f"TOTAL FINAL: ${total_v:,.2f}", ln=True)
                    pdf.ln(10)
                    pdf.set_font("Arial", "I", 10)
                    pdf.multi_cell(0, 10, txt=f"Notas: {notas_venta}")
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    pdf_name = f"{nombre_cliente}_{fec_e}_REM_{n_remision}.pdf".replace(" ", "_")
                    
                    url_e = subir_archivo(evid, "evidencias", "ventas") if evid else None
                    
                    # Uso de upsert para evitar error de archivo duplicado
                    supabase.storage.from_("evidencias").upload(
                        path=f"ventas/{pdf_name}", 
                        file=pdf_bytes, 
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    url_pdf = supabase.storage.from_("evidencias").get_public_url(f"ventas/{pdf_name}")

                    v_ins = {
                        "cliente_id": target_id, "vendedor_id": st.session_state.usuario_id, "sede_id": sede_id_seleccionada,
                        "monto_total": total_v, "monto_credito": credito, "evidencia_url": url_e, "pdf_nota_url": url_pdf, 
                        "fecha_entrega": str(fec_e), "lugar_entrega": lug_e_completo, "tipo_venta": tipo_v, "notas_internas": notas_venta,
                        "cargos_adicionales": {
                            "flete": flete, "maniobra": maniobra, "iva_incluido": aplicar_iva, "monto_iva": iva_monto,
                            "calculo_flete": {"km_ida": km_ida, "gasolina_estimada": gasolina_est, "pago_operador": pago_op}
                        }, 
                        "estatus_pago": "pagado" if credito <= 0 else "pendiente", "num_remision": n_remision
                    }
                    
                    rv = supabase.table("ventas").insert(v_ins).execute()
                    id_v = rv.data[0]['id']
                    
                    for art in st.session_state.carrito:
                        supabase.table("detalles_venta").insert({
                            "venta_id": id_v, "producto_id": art['id'], "cantidad": art['cantidad'], 
                            "precio_unitario": art['precio_base'], "descuento_aplicado": art['descuento'], "subtotal": art['subtotal']
                        }).execute()
                        s_act = float(supabase.table("inventario").select("stock_actual").eq("id", art['id']).single().execute().data['stock_actual'])
                        supabase.table("inventario").update({"stock_actual": s_act - float(art['cantidad'])}).eq("id", art['id']).execute()
                    
                    st.success(f"¡Venta registrada! PDF: {pdf_name}")
                    st.session_state.carrito = []
                    st.rerun()

        with col_btns_2:
            if st.button("📄 GENERAR COTIZACIÓN", use_container_width=True):
                if not st.session_state.carrito:
                    st.error("Agregue materiales para cotizar")
                else:
                    nombre_c = nuevo_cli_nom if c_final_sel == "-- AGREGAR CLIENTE NUEVO --" else c_final_sel
                    pdf_c = FPDF()
                    pdf_c.add_page()
                    pdf_c.set_font("Arial", "B", 16)
                    pdf_c.cell(200, 10, txt="COTIZACIÓN COMERCIAL", ln=True, align='C')
                    pdf_c.set_font("Arial", "", 12)
                    pdf_c.ln(10)
                    pdf_c.cell(200, 10, txt=f"Cliente: {nombre_c}", ln=True)
                    pdf_c.cell(200, 10, txt=f"CP Destino: {cp}", ln=True)
                    pdf_c.ln(5)
                    for item in st.session_state.carrito:
                        pdf_c.cell(100, 10, txt=f"- {item['nombre']}", border=0)
                        pdf_c.cell(40, 10, txt=f"{item['cantidad']} {item['unidad']}", border=0)
                        pdf_c.cell(40, 10, txt=f"${item['subtotal']:,.2f}", border=0, ln=True)
                    pdf_c.ln(5)
                    pdf_c.cell(200, 10, txt=f"Flete Estimado: ${flete:,.2f}", ln=True)
                    pdf_c.set_font("Arial", "B", 14)
                    pdf_c.cell(200, 10, txt=f"TOTAL ESTIMADO: ${total_v:,.2f}", ln=True)
                    pdf_c.set_font("Arial", "I", 10)
                    pdf_c.ln(10)
                    pdf_c.multi_cell(0, 10, txt="Esta cotización no representa un apartado de material y está sujeta a cambios sin previo aviso.")
                    
                    cot_bytes = pdf_c.output(dest='S').encode('latin-1')
                    st.download_button(
                        label="⬇️ Descargar Cotización PDF",
                        data=cot_bytes,
                        file_name=f"Cotizacion_{nombre_c}.pdf",
                        mime="application/pdf"
                    )
                
    elif menu == "Logística y Envíos":
        st.title("🚚 Control de Entregas - CEDIS Perote")
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["📦 Envíos Pendientes", "📜 Historial de Rutas"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Logística y Envíos", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Logística.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)
            
            # --- BUSCADOR UNIVERSAL ---
            st.markdown("### 🔍 Buscador de Salidas")
            busqueda_global = st.text_input("Filtrar por Cliente, Remisión o Sede", placeholder="Ej: Anuar").strip().lower()
            
            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Envíos Pendientes" in tab_name:
                        # 1. Datos iniciales
                        res_envios_finalizados = supabase.table("envios").select("venta_id").in_("estatus", ["terminado", "cancelado", "devuelto"]).execute()
                        ids_excluir = [e['venta_id'] for e in res_envios_finalizados.data]
                        res_v_raw = supabase.table("ventas").select("*, Clientes(*), sedes(*)").order("fecha_entrega").execute()
                        
                        ventas_pendientes = []
                        for v in res_v_raw.data:
                            if v['id'] not in ids_excluir:
                                cumple = True
                                if busqueda_global:
                                    txt = f"{v.get('num_remision','')} {v['Clientes']['nombre']} {v['sedes']['nombre'] if v['sedes'] else ''} {v.get('lugar_entrega','')}".lower()
                                    if busqueda_global not in txt: cumple = False
                                if cumple: ventas_pendientes.append(v)

                        res_unid = supabase.table("unidades").select("*").eq("estado", "activo").execute()
                        res_oper = supabase.table("usuarios").select("id, nombre_usuario").execute()
                        res_todas_sedes = supabase.table("sedes").select("*").execute()
                        
                        u_opts = {f"{u['nombre_unidad']} ({u['placas']})": u['id'] for u in res_unid.data}
                        oper_opts = {o['nombre_usuario']: o['id'] for o in res_oper.data}
                        dict_sedes_regreso = {s['nombre']: s.get('direccion') or s.get('ubicacion') or s['nombre'] for s in res_todas_sedes.data}

                        st.subheader("Asignación y Planificación de Ruta")
                        ventas_opciones = {
                            f"Rem: {v.get('num_remision', 'S/N')} | ${v['monto_total']:,.2f} | {v['Clientes']['nombre']}": v 
                            for v in ventas_pendientes
                        }
                        
                        if ventas_opciones:
                            v_sel_labels = st.multiselect("Seleccionar Ventas para la Ruta", list(ventas_opciones.keys()))
                            
                            if v_sel_labels:
                                ventas_sel = [ventas_opciones[l] for l in v_sel_labels]
                                
                                st.info("🗺️ **Planificador de Ruta**")
                                s_orig = ventas_sel[0].get('sedes')
                                orig_coords = s_orig.get('direccion', s_orig.get('ubicacion', "Perote, Veracruz")) if s_orig else "Perote, Veracruz"
                                destinos = [v['lugar_entrega'] for v in ventas_sel]
                                
                                regreso_nom = st.selectbox("📍 Ubicación de Retorno (Regreso de unidad)", list(dict_sedes_regreso.keys()))
                                dest_final = dict_sedes_regreso[regreso_nom]

                                puntos = [orig_coords] + destinos + [dest_final]
                                ruta_url = "/".join([urllib.parse.quote(str(p).replace("\n", " ").strip()) for p in puntos])
                                full_maps_url = f"https://www.google.com/maps/dir/{ruta_url}"
                                
                                st.link_button("🗺️ Abrir Mapa Optimizado (con CP)", full_maps_url, use_container_width=True, type="primary")

                                with st.form("f_despacho_ruta"):
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        u_envio = st.selectbox("Unidad", list(u_opts.keys()))
                                        op_envio = st.selectbox("Operador Responsable", list(oper_opts.keys()))
                                        acomp = st.text_input("Acompañantes")
                                    with col_b:
                                        km_est = st.number_input("Kilómetros totales (según Maps)", min_value=0.0, step=0.1)
                                        tiempo_est = st.text_input("Tiempo estimado (ej: 1h 20min)", placeholder="Según Maps")
                                        estatus_ini = st.selectbox("Estatus Inicial", ["en preparacion", "listo para enviar", "enviado"])
                                    
                                    if st.form_submit_button("🚀 Confirmar Despacho y Registrar"):
                                        ruta_uuid = f"RUTA-{pd.Timestamp.now().strftime('%m%d-%H%M')}"
                                        for v in ventas_sel:
                                            supabase.table("envios").insert({
                                                "venta_id": v['id'], "unidad_id": u_opts[u_envio], 
                                                "operador_id": oper_opts[op_envio], "acompanantes": acomp,
                                                "ruta_id": ruta_uuid, "estatus": estatus_ini,
                                                "km_estimados": km_est, "tiempo_estimado_min": tiempo_est,
                                                "sede_retorno": regreso_nom
                                            }).execute()
                                        
                                        if estatus_ini == "enviado":
                                            supabase.table("unidades").update({"estado": "en ruta"}).eq("id", u_opts[u_envio]).execute()
                                        st.success(f"Ruta {ruta_uuid} registrada."); st.rerun()
                        else:
                            st.info("✅ No hay ventas pendientes.")

                    elif "Historial de Rutas" in tab_name:
                        st.subheader("📋 Seguimiento Detallado de Rutas")
                        res_env = supabase.table("envios").select("*, ventas(*, Clientes(*), sedes(*)), unidades(*), usuarios(*)").order("fecha_registro", desc=True).execute()
                        
                        if res_env.data:
                            for en in res_env.data:
                                txt_h = f"{en['ventas']['id']} {en['ventas']['Clientes']['nombre']} {en.get('ruta_id','')} {en['ventas'].get('num_remision','')} {en['ventas'].get('lugar_entrega','')}".lower()
                                if busqueda_global and busqueda_global not in txt_h: continue
                                
                                cliente = en['ventas']['Clientes']['nombre']; rem = en['ventas'].get('num_remision', 'S/N'); estatus_actual = en['estatus']
                                
                                with st.expander(f"📦 Rem: {rem} | {cliente} | [{estatus_actual.upper()}] | 🛣️ {en.get('ruta_id','S/R')}"):
                                    col_det, col_act = st.columns([2, 1])
                                    
                                    with col_det:
                                        st.write(f"**Destino:** {en['ventas']['lugar_entrega']}")
                                        
                                        # Mostrar KM y Tiempo Real si ya terminó, de lo contrario mostrar Plan
                                        if estatus_actual == "terminado":
                                            # Buscamos en el historial la nota que contiene los datos reales
                                            res_real = supabase.table("historial_estatus_envios").select("notas").eq("envio_id", en['id']).eq("estatus_nuevo", "terminado").order("fecha_cambio", desc=True).limit(1).execute()
                                            txt_real = f" | {res_real.data[0]['notas']}" if res_real.data and "DATOS REALES" in res_real.data[0]['notas'] else ""
                                            st.write(f"**Resultado Final:** {en.get('km_estimados', 0)} KM Planificados {txt_real}")
                                        else:
                                            st.write(f"**Plan:** {en.get('km_estimados', 0)} KM | Regresa a: {en.get('sede_retorno', 'N/A')} | Tiempo est: {en.get('tiempo_estimado_min', 'N/A')}")
                                        
                                        # Lógica de Tiempo de Retorno: Visible solo si está 'enviado' hasta antes de 'terminado'
                                        estados_activos_ruta = ["enviado", "retrasado", "recibido", "de regreso"]
                                        if estatus_actual in estados_activos_ruta and en.get('tiempo_estimado_min'):
                                            try:
                                                t_str = en['tiempo_estimado_min'].lower()
                                                m_extra = 45  # 45 min fijos de maniobra
                                                if 'h' in t_str: m_extra += int(t_str.split('h')[0].strip()) * 60
                                                if 'min' in t_str: m_extra += int(t_str.split('min')[0].split('h')[-1].strip())
                                                
                                                # Cálculo persistente desde la hora en que pasó a 'enviado' (o registro si no hay historial)
                                                res_envio_f = supabase.table("historial_estatus_envios").select("fecha_cambio").eq("envio_id", en['id']).eq("estatus_nuevo", "enviado").order("fecha_cambio").limit(1).execute()
                                                fecha_base = res_envio_f.data[0]['fecha_cambio'] if res_envio_f.data else en['fecha_registro']
                                                
                                                hora_reg = pd.to_datetime(fecha_base).tz_convert('America/Mexico_City') + pd.Timedelta(minutes=m_extra)
                                                st.success(f"⌛ **Retorno estimado (incl. 45m maniobra):** {hora_reg.strftime('%H:%M')} (Aprox)")
                                            except: pass

                                        st.caption(f"Unidad: {en['unidades']['nombre_unidad']} | Operador: {en['usuarios']['nombre_usuario']}")
                                        dir_m = urllib.parse.quote(str(en['ventas']['lugar_entrega']).strip())
                                        st.link_button("📍 Ver Destino Exacto (Maps)", f"https://www.google.com/maps/search/?api=1&query={dir_m}")

                                        st.markdown("---")
                                        st.caption("🕒 Historial de cambios y evidencias:")
                                        res_h = supabase.table("historial_estatus_envios").select("*").eq("envio_id", en['id']).order("fecha_cambio", desc=True).execute()
                                        if res_h.data:
                                            for h in res_h.data:
                                                f_h = pd.to_datetime(h['fecha_cambio']).tz_convert('America/Mexico_City').strftime('%d/%m %H:%M')
                                                c_txt, c_img = st.columns([0.8, 0.2])
                                                with c_txt:
                                                    st.write(f"• `{f_h}`: **{h['estatus_nuevo'].upper()}**")
                                                    if h.get('notas'): st.caption(f"💬 {h['notas']}")
                                                with c_img:
                                                    if h.get('evidencia_url'):
                                                        st.link_button("📸 Ver", h['evidencia_url'], use_container_width=True)

                                    with col_act:
                                        st.markdown("##### Actualizar Estatus")
                                        opciones = ["en preparacion", "listo para enviar", "enviado", "retrasado", "recibido", "de regreso", "terminado", "cancelado", "devuelto"]
                                        nuevo_est = st.selectbox("Nuevo Estado", opciones, index=opciones.index(en['estatus']) if en['estatus'] in opciones else 0, key=f"sel_{en['id']}")
                                        
                                        with st.form(f"upd_est_{en['id']}"):
                                            km_r, t_r = None, None
                                            if nuevo_est == "terminado":
                                                st.warning("📊 Registro Real de Cierre:")
                                                km_r = st.number_input("Kilometraje Real Final", min_value=0.0, step=0.1, key=f"km_r_{en['id']}")
                                                t_r = st.text_input("Tiempo Real de Ruta", placeholder="Ej: 1h 40min", key=f"t_r_{en['id']}")
                                            
                                            nota_h = st.text_input("Nota / Observaciones", placeholder="Ej. Entregado sin novedad", key=f"nota_{en['id']}")
                                            evid_file = st.file_uploader("Evidencia Fotográfica", type=["jpg", "png"], key=f"file_{en['id']}")
                                            
                                            if st.form_submit_button("Guardar 💾"):
                                                url_evid = subir_archivo(evid_file, "evidencias", "envios") if evid_file else None
                                                upd_data = {"estatus": nuevo_est}
                                                nota_final = nota_h
                                                
                                                if nuevo_est == "terminado":
                                                    upd_data["fecha_recepcion"] = str(pd.Timestamp.now(tz='America/Mexico_City'))
                                                    if km_r is not None and t_r:
                                                        nota_final = f"{nota_h} | DATOS REALES: {km_r}km - {t_r}".strip(" | ")
                                                
                                                supabase.table("envios").update(upd_data).eq("id", en['id']).execute()
                                                supabase.table("historial_estatus_envios").insert({
                                                    "envio_id": en['id'], "estatus_anterior": en['estatus'], "estatus_nuevo": nuevo_est, 
                                                    "usuario_id": st.session_state.usuario_id, "notas": nota_final, "evidencia_url": url_evid
                                                }).execute()
                                                
                                                if nuevo_est in ["terminado", "cancelado", "devuelto"]:
                                                    supabase.table("unidades").update({"estado": "activo"}).eq("id", en['unidad_id']).execute()
                                                st.rerun()
                        else:
                            st.info("No hay registros en el historial.")        

    elif menu == "Clientes":
        st.title("👥 Gestión de Clientes y Recibos")
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["📊 Cartera General", "🔍 Expediente Detallado", "🧾 Ver Recibos"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Clientes", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Clientes.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)
            
            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Cartera General" in tab_name:
                        try:
                            res_c = supabase.table("Clientes").select("*").execute()
                            res_v = supabase.table("ventas").select("cliente_id, monto_total, monto_credito, fecha_venta").execute()
                            df_c, df_v = pd.DataFrame(res_c.data), pd.DataFrame(res_v.data)
                            
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

                    elif "Expediente Detallado" in tab_name:
                        st.subheader("Consulta de Historial por Cliente")
                        res_c_exp = supabase.table("Clientes").select("*").order("nombre").execute()
                        
                        busqueda_exp = st.text_input("🔍 Filtrar cliente para auditar", "").lower()
                        opciones_exp = [c for c in res_c_exp.data if busqueda_exp in c['nombre'].lower()]
                        dict_c_exp = {c['nombre']: c for c in opciones_exp}
                        
                        if dict_c_exp:
                            c_sel_nom = st.selectbox("Seleccionar Cliente", list(dict_c_exp.keys()))
                            
                            if c_sel_nom:
                                c_data = dict_c_exp[c_sel_nom]
                                
                                st.write("📅 **Rango de fechas para el reporte:**")
                                col_f1, col_f2 = st.columns(2)
                                with col_f1:
                                    f_inicio = st.date_input("Desde", value=pd.to_datetime("today") - pd.Timedelta(days=30))
                                with col_f2:
                                    f_fin = st.date_input("Hasta", value=pd.to_datetime("today"))
                                
                                st.divider()
                                
                                col1, col2, col3 = st.columns(3)
                                col1.info(f"**Nombre:**\n\n{c_data['nombre']}")
                                col2.info(f"**WhatsApp:**\n\n{c_data.get('telefono', 'N/A')}")
                                col3.info(f"**Email:**\n\n{c_data.get('email', 'N/A')}")
                                
                                ventas_c = supabase.table("ventas").select("*, usuarios(nombre_usuario)")\
                                    .eq("cliente_id", c_data['id'])\
                                    .gte("fecha_venta", str(f_inicio))\
                                    .lte("fecha_venta", str(f_fin) + " 23:59:59")\
                                    .order("fecha_venta", desc=True).execute()
                                
                                df_v_c = pd.DataFrame(ventas_c.data)
                                
                                ids_ventas_periodo = [v['id'] for v in ventas_c.data] if ventas_c.data else []
                                df_a_c = pd.DataFrame()
                                if ids_ventas_periodo:
                                    abonos_c = supabase.table("abonos").select("*, ventas(num_remision)").in_("venta_id", ids_ventas_periodo).order("fecha_abono", desc=True).execute()
                                    df_a_c = pd.DataFrame(abonos_c.data)

                                m1, m2, m3, m4 = st.columns(4)
                                m1.metric("Total Comprado (Periodo)", f"${df_v_c['monto_total'].sum() if not df_v_c.empty else 0:,.2f}")
                                m2.metric("Deuda Actual", f"${df_v_c['monto_credito'].sum() if not df_v_c.empty else 0:,.2f}")
                                u_c_f = pd.to_datetime(df_v_c['fecha_venta'].iloc[0]).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not df_v_c.empty else "N/A"
                                m3.write(f"**Última Compra:**\n\n{u_c_f}")
                                u_a_f = pd.to_datetime(df_a_c['fecha_abono'].iloc[0]).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M') if not df_a_c.empty else "N/A"
                                m4.write(f"**Último Abono:**\n\n{u_a_f}")

                                if st.button("📥 Generar Estado de Cuenta PDF"):
                                    v_prev = supabase.table("ventas").select("id, monto_total").eq("cliente_id", c_data['id']).lt("fecha_venta", str(f_inicio)).execute()
                                    ids_p = [x['id'] for x in v_prev.data]
                                    a_prev = supabase.table("abonos").select("monto_abono").in_("venta_id", ids_p).lt("fecha_abono", str(f_inicio)).execute() if ids_p else None
                                    
                                    sum_v_prev = sum(float(x['monto_total']) for x in v_prev.data)
                                    sum_a_prev = sum(float(x['monto_abono']) for x in a_prev.data) if a_prev else 0
                                    saldo_anterior_inicial = sum_v_prev - sum_a_prev

                                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                                    pdf.add_page()
                                    pdf.set_font("Arial", 'B', 14)
                                    pdf.cell(0, 10, "CEDIS MOCTEZUMA PEROTE S.A. DE C.V.", ln=True, align='C')
                                    pdf.set_font("Arial", 'B', 12)
                                    pdf.cell(0, 7, "RECONOCIMIENTO DE ADEUDO / RELACIÓN DE ABONOS Y ADEUDOS", ln=True, align='C')
                                    pdf.ln(5)
                                    
                                    pdf.set_font("Arial", 'B', 11)
                                    pdf.cell(0, 7, f"CLIENTE: {c_data['nombre'].upper()}", ln=True)
                                    pdf.cell(0, 7, f"PERIODO: {f_inicio.strftime('%d/%m/%Y')} AL {f_fin.strftime('%d/%m/%Y')}", ln=True)
                                    pdf.ln(5)

                                    pdf.set_fill_color(240, 240, 240)
                                    pdf.set_font("Arial", 'B', 9)
                                    pdf.cell(30, 8, "FECHA", 1, 0, 'C', True)
                                    pdf.cell(110, 8, "DESCRIPCIÓN / DETALLE MATERIALES", 1, 0, 'C', True)
                                    pdf.cell(35, 8, "CARGOS (+)", 1, 0, 'C', True)
                                    pdf.cell(35, 8, "ABONOS (-)", 1, 0, 'C', True)
                                    pdf.cell(35, 8, "SALDO", 1, 1, 'C', True)

                                    pdf.set_font("Arial", size=9)
                                    pdf.cell(30, 7, f_inicio.strftime('%d/%m/%Y'), 1)
                                    pdf.cell(110, 7, "SALDO ANTERIOR ACUMULADO", 1)
                                    pdf.cell(35, 7, "-", 1, 0, 'R')
                                    pdf.cell(35, 7, "-", 1, 0, 'R')
                                    pdf.cell(35, 7, f"${saldo_anterior_inicial:,.2f}", 1, 1, 'R')

                                    movs = []
                                    for _, v in df_v_c.iterrows():
                                        items_v = supabase.table("detalles_venta").select("cantidad, inventario(nombre_producto, unidad_medida)").eq("venta_id", v['id']).execute()
                                        desc_materiales = ", ".join([f"{i['cantidad']} {i['inventario']['unidad_medida']} {i['inventario']['nombre_producto']}" for i in items_v.data])
                                        rem = v.get('num_remision', 'S/N')
                                        movs.append({
                                            'fecha': pd.to_datetime(v['fecha_venta']),
                                            'desc': f"Rem {rem}: {desc_materiales}",
                                            'cargo': float(v['monto_total']),
                                            'abono': 0.0
                                        })
                                    for _, a in df_a_c.iterrows():
                                        rem_abonada = a['ventas']['num_remision'] if a.get('ventas') else "S/N"
                                        nota = f" - Nota: {a['referencia']}" if a.get('referencia') else ""
                                        movs.append({
                                            'fecha': pd.to_datetime(a['fecha_abono']),
                                            'desc': f"Abono a Rem {rem_abonada} - {a['forma_pago']}{nota}",
                                            'cargo': 0.0,
                                            'abono': float(a['monto_abono'])
                                        })
                                    
                                    movs = sorted(movs, key=lambda x: x['fecha'])
                                    saldo_acum = saldo_anterior_inicial
                                    total_c = 0.0
                                    total_a = 0.0

                                    for m in movs:
                                        saldo_acum += (m['cargo'] - m['abono'])
                                        total_c += m['cargo']
                                        total_a += m['abono']
                                        
                                        x_pos = pdf.get_x()
                                        y_pos = pdf.get_y()
                                        pdf.set_xy(x_pos + 30, y_pos)
                                        pdf.multi_cell(110, 6, m['desc'], 0, 'L')
                                        end_y = pdf.get_y()
                                        h = max(7, end_y - y_pos)
                                        
                                        pdf.set_xy(x_pos, y_pos)
                                        pdf.cell(30, h, m['fecha'].strftime('%d/%m/%Y'), 1)
                                        pdf.cell(110, h, "", 1)
                                        pdf.set_xy(x_pos + 140, y_pos)
                                        pdf.cell(35, h, f"${m['cargo']:,.2f}" if m['cargo'] > 0 else "-", 1, 0, 'R')
                                        pdf.cell(35, h, f"${m['abono']:,.2f}" if m['abono'] > 0 else "-", 1, 0, 'R')
                                        pdf.cell(35, h, f"${saldo_acum:,.2f}", 1, 1, 'R')

                                    pdf.set_font("Arial", 'B', 10)
                                    pdf.cell(140, 9, "TOTALES DEL PERIODO:", 1, 0, 'R', True)
                                    pdf.cell(35, 9, f"${total_c:,.2f}", 1, 0, 'R', True)
                                    pdf.cell(35, 9, f"${total_a:,.2f}", 1, 0, 'R', True)
                                    pdf.cell(35, 9, f"${saldo_acum:,.2f}", 1, 1, 'R', True)
                                    
                                    pdf.ln(10)
                                    pdf.set_font("Arial", 'B', 10)
                                    pdf.cell(0, 10, "ACEPTO DE CONFORMIDAD EL SALDO MENCIONADO", 0, 1, 'C')
                                    pdf.ln(5)
                                    pdf.cell(0, 10, "_______________________________________", 0, 1, 'C')
                                    pdf.cell(0, 5, f"FIRMA DEL CLIENTE: {c_data['nombre'].upper()}", 0, 1, 'C')

                                    nombre_archivo = f"EdoCuenta_{c_data['nombre'].replace(' ', '_')}_{f_inicio}_al_{f_fin}.pdf"
                                    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
                                    st.download_button(label="💾 Descargar Estado de Cuenta", data=pdf_bytes, file_name=nombre_archivo, mime="application/pdf")

                                st.write("### 📜 Historial de Movimientos (Vista rápida)")
                                t_ventas_tab, t_abonos_tab = st.tabs(["🛍️ Compras", "💰 Abonos Realizados"])
                                
                                with t_ventas_tab:
                                    if not df_v_c.empty:
                                        for _, row in df_v_c.iterrows():
                                            fecha_mx = pd.to_datetime(row['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y %H:%M')
                                            col_info, col_btn = st.columns([4, 1])
                                            with col_info:
                                                rem = row.get('num_remision', 'S/N')
                                                st.write(f"**Remisión:** `{rem}` | **Fecha:** {fecha_mx}")
                                                st.caption(f"Total: ${row['monto_total']:,.2f} | Restante: ${row['monto_credito']:,.2f}")
                                            with col_btn:
                                                if st.button(f"Recibo 🧾", key=f"btn_exp_{row['id']}"):
                                                    st.session_state.ver_id = row['id']
                                                    st.rerun()
                                            st.divider()
                                    else: st.write("No hay registros en este rango de fechas.")
                                
                                with t_abonos_tab:
                                    if not df_a_c.empty:
                                        df_a_c['fecha_mx'] = pd.to_datetime(df_a_c['fecha_abono']).dt.tz_convert('America/Mexico_City').dt.strftime('%d/%m/%Y %H:%M')
                                        df_a_c['Remisión'] = df_a_c['ventas'].apply(lambda x: x['num_remision'] if x else 'S/N')
                                        cols_a = [c for c in ['fecha_mx', 'Remisión', 'monto_abono', 'forma_pago', 'referencia'] if c in df_a_c.columns]
                                        st.dataframe(df_a_c[cols_a], use_container_width=True, hide_index=True)
                                    else: st.write("No hay abonos en este rango de fechas.")
                        else:
                            st.info("No se encontraron clientes.")

                    elif "Ver Recibos" in tab_name:
                        st.subheader("Generación de Recibos")
                        busqueda_rec = st.text_input("🔍 Buscar recibos por nombre de cliente", "").lower()
                        res_rec = supabase.table("ventas").select("id, num_remision, fecha_venta, monto_total, Clientes(nombre)").order("fecha_venta", desc=True).execute()
                        recibos_filtrados = [r for r in res_rec.data if busqueda_rec in r['Clientes']['nombre'].lower()]
                        
                        for r in recibos_filtrados[:20]:
                            fecha_mx = pd.to_datetime(r['fecha_venta']).tz_convert('America/Mexico_City').strftime('%d/%m/%Y')
                            rem = r.get('num_remision', 'S/N')
                            col_btn, col_info = st.columns([1, 4])
                            with col_btn:
                                if st.button(f"Ver 📄", key=f"btn_list_{r['id']}"):
                                    st.session_state.ver_id = r['id']
                                    st.rerun()
                            with col_info:
                                st.write(f"**{r['Clientes']['nombre']}** (Rem: {rem}) - ${r['monto_total']:,.2f} ({fecha_mx})")
                        
                        if not recibos_filtrados:
                            st.info("No se encontraron recibos.")



# --- PÁGINA: REGISTRAR ABONO (COBRANZA CON EVIDENCIA) ---
    elif menu == "Registrar Abono":
        st.title("💸 Cobranza CEDIS Perote")
        
        # 1. Consultamos ventas con deuda
        res_v = supabase.table("ventas").select("id, monto_total, monto_credito, Clientes(nombre)").gt("monto_credito", 0).execute()
        
        if res_v.data:
            # Diccionario para identificar la deuda seleccionada
            dict_d = {f"{v['Clientes']['nombre']} (Saldo Actual: ${v['monto_credito']:,.2f})": v for v in res_v.data}
            
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

                if st.form_submit_button("✅ Enviar para Revisión"):
                    url_evidencia = subir_archivo(evid_abono, "evidencias", "abonos") if evid_abono else None
                    
                    # Insertar el abono con estatus PENDIENTE (por defecto en DB o explícito aquí)
                    nuevo_abono = {
                        "venta_id": deuda_seleccionada['id'],
                        "vendedor_id": st.session_state.usuario_id,
                        "monto_abono": ab,
                        "forma_pago": forma_pago,
                        "evidencia_url": url_evidencia,
                        "referencia": referencia,
                        "estatus_aprobacion": "pendiente" # IMPORTANTE
                    }
                    
                    try:
                        # REGISTRAMOS EL ABONO PERO NO TOCAMOS LA TABLA VENTAS AQUÍ
                        supabase.table("abonos").insert(nuevo_abono).execute()
                        
                        st.warning(f"Abono de ${ab} registrado. Aparecerá en el saldo una vez que el administrador lo apruebe.")
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
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["📋 Inventario", "➕ Alta de Unidad", "🛠️ Mantenimiento", "⛽ Combustible"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Flota y Unidades", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Flota.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)
            
            # Consultas base
            # Traemos la información de la unidad y el nombre del usuario relacionado
            res_u = supabase.table("unidades").select("*, usuarios(nombre_usuario)").order("nombre_unidad").execute()
            res_c_total = supabase.table("combustible_unidades").select("costo_total").execute()
            res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
            
            df_u = pd.DataFrame(res_u.data)
            df_c_total = pd.DataFrame(res_c_total.data)
            dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}
            
            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Inventario" in tab_name:
                        if not df_u.empty:
                            # Cálculos para los métricos
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
                                # Icono dinámico según estado
                                emoji = "🟢" if u['estado'] == "activo" else "🟠" if u['estado'] == "en ruta" else "🔴"
                                # Título detallado con Modelo y Año
                                titulo_exp = f"{emoji} {u['nombre_unidad']} | {u.get('modelo', 'Sin Modelo')} {u.get('anio', '')} | {u['placas']}"
                                
                                with st.expander(titulo_exp):
                                    col_img, col_info = st.columns([1, 2])
                                    
                                    with col_img:
                                        if u.get('foto_unidad_url'):
                                            st.image(u['foto_unidad_url'], use_container_width=True)
                                        else: st.info("Sin fotografía.")

                                    with col_info:
                                        st.markdown(f"### Detalles Técnicos")
                                        c_det1, c_det2 = st.columns(2)
                                        with c_det1:
                                            st.write(f"**Serie/VIN:** `{u.get('serie', 'N/A')}`")
                                            st.write(f"**Tipo:** {u.get('tipo', 'N/A')}")
                                            st.write(f"**Color:** {u.get('color', 'N/A')}")
                                            st.write(f"**Dueño:** {u.get('dueno', 'N/A')}")
                                        with c_det2:
                                            # Extraer nombre del responsable desde la relación
                                            resp_vinc = u['usuarios']['nombre_usuario'] if u.get('usuarios') else "No asignado"
                                            st.write(f"**Responsable:** {resp_vinc}")
                                            st.write(f"**KM Actual:** {u.get('kilometraje_actual', 0):,} km")
                                            st.write(f"**Estado:** :bold[{u['estado'].upper()}]")
                                            if u.get('nota_estado'):
                                                st.caption(f"Nota: {u['nota_estado']}")

                                    st.divider()
                                    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs(["🛠️ Hist. Mantenimiento", "⛽ Hist. Combustible", "📦 Envíos Asignados", "📄 Documentación"])
                                    
                                    with sub_t1:
                                        res_hm = supabase.table("historial_unidades").select("*").eq("unidad_id", u['id']).order("fecha_ingreso", desc=True).execute()
                                        if res_hm.data: st.dataframe(pd.DataFrame(res_hm.data)[['fecha_ingreso', 'costo_total', 'descripcion_falla']], use_container_width=True, hide_index=True)
                                        else: st.info("Sin registros de taller.")

                                    with sub_t2:
                                        res_hg = supabase.table("combustible_unidades").select("*").eq("unidad_id", u['id']).order("fecha", desc=True).execute()
                                        if res_hg.data: st.dataframe(pd.DataFrame(res_hg.data)[['fecha', 'litros', 'costo_total']], use_container_width=True, hide_index=True)
                                        else: st.info("Sin registros de combustible.")

                                    with sub_t3:
                                        res_he = supabase.table("envios").select("*, ventas(Clientes(nombre))").eq("unidad_id", u['id']).order("fecha_registro", desc=True).execute()
                                        if res_he.data:
                                            env_list = [{"Fecha": e['fecha_registro'][:10], "Cliente": e['ventas']['Clientes']['nombre'], "Estatus": e['estatus']} for e in res_he.data]
                                            st.table(pd.DataFrame(env_list))
                                        else: st.info("Sin envíos registrados.")

                                    with sub_t4:
                                        st.write("**Documentos Oficiales:**")
                                        d_col1, d_col2, d_col3 = st.columns(3)
                                        for col, label, key in [(d_col1, "Seguro", "url_seguro"), (d_col2, "Tenencia", "url_tenencia"), (d_col3, "Verificación", "url_verificacion")]:
                                            if u.get(key): col.link_button(f"Ver {label} 📄", u[key], use_container_width=True)
                                            else: col.warning(f"Falta {label}")
                                        
                                        # Mostrar la lista de Documentos Varios
                                        docs_varios = u.get('urls_documentos_varios', [])
                                        if docs_varios:
                                            st.markdown("---")
                                            st.write("**Otros Documentos:**")
                                            for idx, link in enumerate(docs_varios):
                                                st.markdown(f"🔗 [Documento Adicional {idx+1}]({link})")
                        else:
                            st.warning("No hay unidades en el inventario.")

                    elif "Alta de Unidad" in tab_name:
                        st.subheader("Registrar Nueva Unidad")
                        with st.form("f_nueva_unidad", clear_on_submit=True):
                            c1, c2 = st.columns(2)
                            with c1:
                                n_u = st.text_input("Nombre de la Unidad (Ej: Camioneta 01)")
                                mod_u = st.text_input("Modelo (Ej: F-150)")
                                anio_u = st.number_input("Año", min_value=1990, max_value=2030, value=2025)
                                p_u = st.text_input("Placas")
                                s_u = st.text_input("Número de Serie / VIN")
                                t_u = st.selectbox("Tipo de Vehículo", ["Particular","Tolba","Plana","Tracto Camión","Montacarga"])
                                
                            with c2:
                                d_u = st.text_input("Dueño / Propietario")
                                col_u = st.text_input("Color")
                                resp_nom_u = st.selectbox("Responsable Fijo (Usuario)", list(dict_users.keys()))
                                km_u = st.number_input("Kilometraje Inicial", min_value=0)
                                foto_u = st.file_uploader("Fotografía de la Unidad", type=["jpg", "png"])
                            
                            st.markdown("---")
                            st.write("📂 **Cargar Documentación**")
                            cd1, cd2, cd3 = st.columns(3)
                            with cd1: f_seguro = st.file_uploader("Póliza de Seguro", type=["pdf", "jpg", "png"])
                            with cd2: f_tenencia = st.file_uploader("Comprobante Tenencia", type=["pdf", "jpg", "png"])
                            with cd3: f_verif = st.file_uploader("Verificación", type=["pdf", "jpg", "png"])
                            
                            f_varios = st.file_uploader("Documentos Varios (Múltiple)", type=["pdf", "jpg", "png"], accept_multiple_files=True)

                            if st.form_submit_button("💾 Guardar Nueva Unidad"):
                                if not n_u or not p_u:
                                    st.error("Nombre y Placas son obligatorios.")
                                else:
                                    url_foto = subir_archivo(foto_u, "evidencias", "unidades") if foto_u else None
                                    url_s = subir_archivo(f_seguro, "evidencias", "documentos") if f_seguro else None
                                    url_t = subir_archivo(f_tenencia, "evidencias", "documentos") if f_tenencia else None
                                    url_v = subir_archivo(f_verif, "evidencias", "documentos") if f_verif else None
                                    
                                    urls_varios = []
                                    if f_varios:
                                        folder_name = n_u.replace(" ", "_")
                                        for f in f_varios:
                                            u_v = subir_archivo(f, "evidencias", f"documentos/{folder_name}")
                                            if u_v: urls_varios.append(u_v)

                                    data_u = {
                                        "nombre_unidad": n_u, 
                                        "modelo": mod_u,
                                        "anio": anio_u,
                                        "placas": p_u, 
                                        "serie": s_u, 
                                        "tipo": t_u, 
                                        "color": col_u, 
                                        "responsable_id": dict_users[resp_nom_u], 
                                        "kilometraje_actual": km_u,
                                        "dueno": d_u,
                                        "foto_unidad_url": url_foto, 
                                        "estado": "activo",
                                        "url_seguro": url_s, 
                                        "url_tenencia": url_t, 
                                        "url_verificacion": url_v,
                                        "urls_documentos_varios": urls_varios
                                    }
                                    supabase.table("unidades").insert(data_u).execute()
                                    st.success(f"✅ Unidad {n_u} registrada con éxito.")
                                    st.rerun()

                    elif "Mantenimiento" in tab_name:
                        st.subheader("🛠️ Control de Taller y Reparaciones")
                        if not df_u.empty:
                            u_list = {f"{u['nombre_unidad']} ({u['placas']})": u for _, u in df_u.iterrows()}
                            u_sel_nom = st.selectbox("Seleccionar Unidad", list(u_list.keys()))
                            u_info = u_list[u_sel_nom]
                            
                            col_m1, col_m2 = st.columns(2)
                            
                            with col_m1:
                                st.markdown("### 📥 Registrar Entrada")
                                with st.form("f_entrada_taller", clear_on_submit=True):
                                    f_in = st.date_input("Fecha de Ingreso")
                                    taller = st.text_input("Taller / Mecánico")
                                    falla = st.text_area("Motivo de ingreso / Falla")
                                    
                                    if st.form_submit_button("🔨 Enviar a Reparación"):
                                        supabase.table("unidades").update({
                                            "estado": "en reparación",
                                            "nota_estado": falla,
                                            "ultima_entrada_taller": str(f_in),
                                            "encargado_reparacion": taller
                                        }).eq("id", u_info['id']).execute()
                                        st.rerun()

                            with col_m2:
                                st.markdown("### 📤 Registrar Salida")
                                if u_info['estado'] == "en reparación":
                                    with st.form("f_salida_taller", clear_on_submit=True):
                                        f_out = st.date_input("Fecha de Salida")
                                        costo = st.number_input("Costo Final de Reparación ($)", min_value=0.0, step=100.0)
                                        evid_r = st.file_uploader("Evidencia / Factura", type=["jpg", "png", "pdf"])
                                        
                                        if st.form_submit_button("✅ Finalizar Reparación"):
                                            url_r = subir_archivo(evid_r, "evidencias", "reparaciones") if evid_r else None
                                            supabase.table("unidades").update({
                                                "estado": "activo",
                                                "nota_estado": "Reparación finalizada",
                                                "ultima_salida_taller": str(f_out),
                                                "ultimo_costo_reparacion": costo
                                            }).eq("id", u_info['id']).execute()
                                            
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
                                            st.rerun()
                                else:
                                    st.info("La unidad está ACTIVA.")
                        else:
                            st.warning("No hay unidades registradas.")

                    elif "Combustible" in tab_name:
                        st.subheader("⛽ Carga de Gasolina")
                        if not df_u.empty:
                            u_c_dict = {f"{u['nombre_unidad']} ({u['placas']})": u for _, u in df_u.iterrows()}
                            u_c_sel = st.selectbox("Seleccionar Unidad para Gasolina", list(u_c_dict.keys()))
                            u_info = u_c_dict[u_c_sel]

                            with st.form("f_combustible", clear_on_submit=True):
                                c_g1, c_g2 = st.columns(2)
                                with c_g1:
                                    f_g = st.date_input("Fecha Carga")
                                    km_actual_bd = int(u_info.get('kilometraje_actual', 0))
                                    km_g = st.number_input("Kilometraje al cargar", min_value=km_actual_bd, value=km_actual_bd)
                                with c_g2:
                                    lits = st.number_input("Litros", min_value=1.0, step=0.1)
                                    pago = st.number_input("Costo Total ($)", min_value=1.0, step=10.0)
                                    ticket = st.file_uploader("Ticket", type=["jpg", "png", "jpeg"])

                                if st.form_submit_button("Registrar Carga"):
                                    ppl = pago / lits if lits > 0 else 0
                                    url_t = subir_archivo(ticket, "evidencias", "combustible") if ticket else None
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
                                    supabase.table("combustible_unidades").insert(data_g).execute()
                                    supabase.table("unidades").update({"kilometraje_actual": km_g}).eq("id", u_info['id']).execute()
                                    st.success("✅ Carga registrada")
                                    st.rerun()

    
                    
    elif menu == "Gestión de Gastos":
        st.title("💰 Control de Gastos - CEDIS Perote")
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["➕ Registrar Gasto", "📜 Historial y Auditoría"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Gestión de Gastos", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Gastos.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)

            # Consultas base
            res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
            dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}
            
            res_u = supabase.table("unidades").select("id, nombre_unidad, placas, kilometraje_actual").order("nombre_unidad").execute()
            dict_unidades = {f"{u['nombre_unidad']} ({u['placas']})": u for u in res_u.data}

            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Registrar Gasto" in tab_name:
                        st.subheader("Nuevo Registro")
                        
                        c_top1, c_top2 = st.columns(2)
                        with c_top1:
                            t_gasto = st.selectbox("Tipo de Gasto", [
                                "Impuestos", "Salarios", "Compra de Mercancía", "Servicios (Luz/Agua)", 
                                "Mantenimiento", "Publicidad", "Herramientas", "Viáticos", "Renta","Combustible"
                            ])
                        with c_top2:
                            responsable_nom = st.selectbox("Responsable del Gasto", list(dict_users.keys()))
                            responsable_id = dict_users[responsable_nom]

                        unidad_sel_id = None
                        litros_g = 0.0
                        km_g = 0
                        dias_t = None
                        beneficiario_id = None
                        
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
                        
                        elif t_gasto == "Salarios":
                            st.info("👥 **Detalles de Nómina**")
                            col_sal1, col_sal2 = st.columns(2)
                            with col_sal1:
                                empleado_nom = st.selectbox("Personal a quien se paga", list(dict_users.keys()), key="sal_emp")
                                beneficiario_id = dict_users[empleado_nom]
                            with col_sal2:
                                dias_t = st.number_input("Días trabajados", min_value=1, max_value=31, value=7)

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
                                    
                                    ins_data = {
                                        "usuario_id": responsable_id,
                                        "tipo_gasto": t_gasto,
                                        "subcategoria": sub_g,
                                        "monto": monto_g,
                                        "descripcion": desc_g,
                                        "estatus_gasto": estatus_g,
                                        "evidencia_url": url_g,
                                        "dias_trabajados": dias_t,
                                        "beneficiario_id": beneficiario_id
                                    }
                                    supabase.table("gastos").insert(ins_data).execute()

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
                                        supabase.table("unidades").update({"kilometraje_actual": km_g}).eq("id", unidad_sel_id).execute()
                                        st.toast("⛽ Datos de flota actualizados")

                                    st.success(f"✅ Gasto registrado con éxito")
                                    st.rerun()

                    elif "Historial y Auditoría" in tab_name:
                        st.subheader("Buscador de Gastos")
                        # CORRECCIÓN AQUÍ: Especificamos la relación exacta !gastos_usuario_id_fkey
                        res_gastos = supabase.table("gastos").select("*, responsable:usuarios!gastos_usuario_id_fkey(nombre_usuario), beneficiario:usuarios!gastos_beneficiario_id_fkey(nombre_usuario)").order("fecha_registro", desc=True).execute()
                        
                        if res_gastos.data:
                            for g in res_gastos.data:
                                label_expander = f"💰 {g['tipo_gasto']} - ${g['monto']:,.2f} ({g['fecha_registro'][:10]})"
                                with st.expander(label_expander):
                                    col_i, col_a = st.columns([2, 1])
                                    
                                    with col_i:
                                        # Usamos los alias definidos en el select
                                        resp_nom = g.get('responsable', {}).get('nombre_usuario', 'N/A')
                                        st.write(f"**Responsable:** {resp_nom}")
                                        
                                        if g['tipo_gasto'] == "Salarios":
                                            bene_nom = g.get('beneficiario', {}).get('nombre_usuario', 'N/A')
                                            st.write(f"**Pagado a:** {bene_nom}")
                                            st.write(f"**Días trabajados:** {g.get('dias_trabajados', 'N/A')}")
                                        
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

        if isinstance(rango, (list, tuple)) and len(rango) == 2:
            f_inicio, f_fin = rango
            f_ini_str = str(f_inicio)
            f_fin_str = str(f_fin)
            
            # --- CONSULTAS A SUPABASE ---
            q_v = supabase.table("ventas").select("*, Clientes(nombre), sedes(nombre)").gte("fecha_entrega", f_ini_str).lte("fecha_entrega", f_fin_str)
            if sede_sel_nom != "Todas":
                q_v = q_v.eq("sede_id", dict_sedes[sede_sel_nom])
            res_v = q_v.execute()
            df_v = pd.DataFrame(res_v.data)

            # CORRECCIÓN DE AMBIGÜEDAD: Se usan los alias responsable y beneficiario
            q_g = supabase.table("gastos").select("""
                *,
                responsable:usuarios!gastos_usuario_id_fkey(nombre_usuario),
                beneficiario:usuarios!gastos_beneficiario_id_fkey(nombre_usuario)
            """).gte("fecha_registro", f_ini_str).lte("fecha_registro", f_fin_str)
            res_g = q_g.execute()
            df_g = pd.DataFrame(res_g.data)

            res_m = supabase.table("historial_unidades").select("*, unidades(*)").gte("fecha_ingreso", f_ini_str).lte("fecha_ingreso", f_fin_str).execute()
            df_m = pd.DataFrame(res_m.data)
            res_gas = supabase.table("combustible_unidades").select("*, unidades(*)").gte("fecha", f_ini_str).lte("fecha", f_fin_str).execute()
            df_gas = pd.DataFrame(res_gas.data)

            # --- PROCESAMIENTO ---
            if not df_v.empty: df_v = df_v.drop_duplicates(subset=['id'])
            if not df_g.empty: df_g = df_g.drop_duplicates(subset=['id'])
            if not df_m.empty: df_m = df_m.drop_duplicates(subset=['id'])
            if not df_gas.empty: df_gas = df_gas.drop_duplicates(subset=['id'])

            total_ingresos = pd.to_numeric(df_v['monto_total']).sum() if not df_v.empty else 0.0
            total_ventas_count = len(df_v)
            cartera_pendiente = pd.to_numeric(df_v['monto_credito']).sum() if not df_v.empty else 0.0
            g_generales = pd.to_numeric(df_g[df_g['tipo_gasto'] != 'Combustible']['monto']).sum() if not df_g.empty else 0.0
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
            
            if total_ingresos > 0 or total_egresos > 0:
                st.subheader("📊 Comparativo Ingresos vs Gastos")
                df_comp = pd.DataFrame({"Concepto": ["Ventas Totales","Utilidad Neta", "Egresos"], "Monto": [total_ingresos,utilidad, total_egresos]})
                st.bar_chart(df_comp.set_index("Concepto"))
            
            st.divider()
            st.subheader("📝 Detalle de Operaciones Rápidas")
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
                else: st.caption("Sin ventas.")

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
                else: st.caption("Sin deudas.")

            with col_t3:
                st.write("**📉 Listado de Gastos**")
                if not df_g.empty:
                    df_g_tabla = pd.DataFrame([{
                        "Fecha": pd.to_datetime(g['fecha_registro']).strftime('%d/%m/%Y'),
                        "Responsable": g['responsable']['nombre_usuario'] if g.get('responsable') else "N/A",
                        "Categoría": g['tipo_gasto'],
                        "Monto": f"${float(g['monto']):,.2f}"
                    } for _, g in df_g.iterrows()])
                    st.dataframe(df_g_tabla, use_container_width=True, hide_index=True)
                else: st.caption("Sin gastos.")

            # --- TABLA MAESTRA DE VENTAS ---
            st.divider()
            st.subheader("📋 Información Maestra de Ventas")
            if not df_v.empty:
                master_data_v = []
                for _, v in df_v.iterrows():
                    cargos = v.get('cargos_adicionales', {})
                    flete_det = cargos.get('calculo_flete', {})
                    master_data_v.append({
                        "Remisión": v.get('num_remision', 'S/N'),
                        "Fecha Venta": pd.to_datetime(v['fecha_venta']).strftime('%d/%m/%Y'),
                        "Cliente": v['Clientes']['nombre'] if v.get('Clientes') else "N/A",
                        "Sede": v['sedes']['nombre'] if v.get('sedes') else "N/A",
                        "Tipo": v.get('tipo_venta', 'Público'),
                        "Monto Total": float(v['monto_total']),
                        "Saldo Cred.": float(v['monto_credito']),
                        "IVA": float(v.get('monto_iva', 0)),
                        "Flete": float(cargos.get('flete', 0)),
                        "Maniobra": float(cargos.get('maniobra', 0)),
                        "Km Ida": flete_det.get('km_ida', 0),
                        "Gasolina Est.": float(flete_det.get('gasolina_estimada', 0)),
                        "Estatus Pago": v['estatus_pago'].upper(),
                        "PDF": v.get('pdf_nota_url', '')
                    })
                df_master_v = pd.DataFrame(master_data_v)
                st.dataframe(df_master_v, column_config={"PDF": st.column_config.LinkColumn("Nota PDF"), "Monto Total": st.column_config.NumberColumn(format="$%.2f"), "Saldo Cred.": st.column_config.NumberColumn(format="$%.2f")}, use_container_width=True, hide_index=True)
                
                csv_v = df_master_v.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Descargar Reporte Maestro Ventas (CSV)", data=csv_v, file_name=f"Reporte_Ventas_{f_ini_str}.csv", mime="text/csv")
            else:
                st.info("No hay datos de ventas.")

            # --- TABLA MAESTRA DE GASTOS ---
            st.divider()
            st.subheader("💸 Información Maestra de Gastos")
            master_gastos = []
            if not df_g.empty:
                for _, g in df_g.iterrows():
                    beneficiario = g['beneficiario']['nombre_usuario'] if g.get('beneficiario') else "N/A"
                    master_gastos.append({
                        "Fecha": pd.to_datetime(g['fecha_registro']).strftime('%d/%m/%Y'),
                        "Tipo": "General", "Categoría": g['tipo_gasto'], 
                        "Subcat": g.get('subcategoria', 'N/A'),
                        "Descripción": g.get('descripcion', 'S/N'), 
                        "Beneficiario": beneficiario,
                        "Monto": float(g['monto']),
                        "Registró": g['responsable']['nombre_usuario'] if g.get('responsable') else "N/A"
                    })
            if not df_m.empty:
                for _, m in df_m.iterrows():
                    u_nombre = m['unidades']['nombre_unidad'] if m.get('unidades') else "Unidad"
                    u_placas = m['unidades']['placas'] if m.get('unidades') else ""
                    master_gastos.append({
                        "Fecha": pd.to_datetime(m['fecha_ingreso']).strftime('%d/%m/%Y'),
                        "Tipo": "Mantenimiento", "Categoría": "Taller", 
                        "Subcat": f"{u_nombre} ({u_placas})",
                        "Descripción": m.get('descripcion_falla', 'S/N'), 
                        "Beneficiario": m.get('encargado_taller', 'N/A'),
                        "Monto": float(m['costo_total']),
                        "Registró": "Taller/Flota"
                    })
            if not df_gas.empty:
                for _, gs in df_gas.iterrows():
                    u_nombre = gs['unidades']['nombre_unidad'] if gs.get('unidades') else "Unidad"
                    u_placas = gs['unidades']['placas'] if gs.get('unidades') else ""
                    master_gastos.append({
                        "Fecha": pd.to_datetime(gs['fecha']).strftime('%d/%m/%Y'),
                        "Tipo": "Combustible", "Categoría": "Gasolina", 
                        "Subcat": f"{u_nombre} ({u_placas})",
                        "Descripción": f"Litros: {gs.get('litros', 0)}", 
                        "Beneficiario": "Gasolinera",
                        "Monto": float(gs['costo_total']),
                        "Registró": "Operador"
                    })

            if master_gastos:
                df_master_g = pd.DataFrame(master_gastos).sort_values(by="Fecha", ascending=False)
                st.dataframe(df_master_g, column_config={"Monto": st.column_config.NumberColumn(format="$%.2f")}, use_container_width=True, hide_index=True)
                
                csv_g = df_master_g.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Descargar Reporte Maestro Gastos (CSV)", data=csv_g, file_name=f"Reporte_Gastos_{f_ini_str}.csv", mime="text/csv")
            else:
                st.info("No hay gastos registrados.")

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
                    # El saldo real es DIRECTAMENTE lo que dice la columna monto_credito
                    saldo_restante = float(row.get('monto_credito', 0))
                    
                    # Traemos abonos para verificar si hay alguno pendiente de aprobar
                    res_a = supabase.table("abonos").select("estatus_aprobacion").eq("venta_id", row['id']).execute()
                    abonos_data = res_a.data
                    tiene_pendientes = any(a['estatus_aprobacion'] == "pendiente" for a in abonos_data)
                    
                    # Una venta está PAGADA solo si el saldo es 0 Y no hay abonos pendientes de validar
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
                    saldo_actual_db = float(v.get('monto_credito', 0))
                    
                    # Consultamos abonos
                    res_a = supabase.table("abonos").select("*, usuarios(nombre_usuario)").eq("venta_id", v['id']).order("fecha_abono", desc=True).execute()
                    
                    # Cálculo visual: Lo abonado es Total - Saldo Actual
                    total_abonado_real = monto_total - saldo_actual_db
                    
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
                            st.metric("Total Abonado", f"${total_abonado_real:,.2f}")
                            st.metric("Saldo Pendiente", f"${max(0.0, saldo_actual_db):,.2f}", delta_color="inverse")
                            
                            if v['evidencia_url']:
                                st.link_button("Ver Comprobante Venta 📄", v['evidencia_url'])

                        if res_a.data:
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
                                            monto_a_restar = float(abono['monto_abono'])
                                            # 1. Aprobar abono
                                            supabase.table("abonos").update({"estatus_aprobacion": "aprobado", "aprobado_por": st.session_state.get('nombre_usuario', 'Admin'), "fecha_revision": "now()"}).eq("id", abono['id']).execute()
                                            # 2. Restar del saldo de la venta
                                            nuevo_saldo = max(0.0, saldo_actual_db - monto_a_restar)
                                            supabase.table("ventas").update({"monto_credito": nuevo_saldo}).eq("id", v['id']).execute()
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
        
        # Definimos todas las tabs disponibles
        tabs_disponibles = ["➕ Registrar Sede", "🏢 Inventario de Sedes", "📜 Historial de Cambios"]
        
        # Filtramos según el rol del usuario
        tabs_permitidas = filtrar_tabs_por_rol(rol, "Gestión de Sedes", tabs_disponibles)
        
        if len(tabs_permitidas) == 0:
            st.warning("⚠️ No tienes permisos para ver ninguna sección de Sedes.")
        else:
            # Creamos las tabs dinámicamente
            tabs = st.tabs(tabs_permitidas)

            # Consultas base
            res_users = supabase.table("usuarios").select("id, nombre_usuario").execute()
            dict_users = {u['nombre_usuario']: u['id'] for u in res_users.data}

            for i, tab_name in enumerate(tabs_permitidas):
                with tabs[i]:
                    if "Registrar Sede" in tab_name:
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

                    elif "Inventario de Sedes" in tab_name:
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
                        else:
                            st.info("No hay sedes registradas.")

                    elif "Historial de Cambios" in tab_name:
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











