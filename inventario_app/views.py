from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q
from .models import Categoria, Repuesto, MovimientoStock, ParametroCategoria, ParametroRepuesto


def login_view(request):
    """Vista de inicio de sesión"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('inventario:lista_repuestos')
    else:
        form = AuthenticationForm()
    
    return render(request, 'inventario_app/login.html', {'form': form})


def logout_view(request):
    """Cerrar sesión"""
    logout(request)
    return redirect('inventario:login')


@login_required
def inicio(request):
    return redirect('inventario:lista_repuestos')


@login_required
def lista_repuestos(request):
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('q')
    
    repuestos = Repuesto.objects.all()
    
    if categoria_id:
        repuestos = repuestos.filter(categoria_id=categoria_id)
    
    if busqueda:
        repuestos = repuestos.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo_interno__icontains=busqueda) |
            Q(numero_parte_haas__icontains=busqueda)
        )
    
    categorias = Categoria.objects.all()
    
    return render(request, 'inventario_app/lista_repuestos.html', {
        'repuestos': repuestos,
        'categorias': categorias,
        'categoria_actual': categoria_id,
        'busqueda': busqueda,
    })


@login_required
def detalle_repuesto(request, pk):
    repuesto = get_object_or_404(Repuesto, pk=pk)
    movimientos = repuesto.movimientos.all().order_by('-fecha')[:10]
    
    # Obtener los parámetros específicos de este repuesto
    parametros = repuesto.parametros.all()
    
    return render(request, 'inventario_app/detalle_repuesto.html', {
        'repuesto': repuesto,
        'movimientos': movimientos,
        'parametros': parametros,
    })


@login_required
def registrar_movimiento(request):
    if request.method == 'POST':
        repuesto_id = request.POST.get('repuesto')
        tipo = request.POST.get('tipo')
        cantidad = int(request.POST.get('cantidad'))
        notas = request.POST.get('notas', '')
        
        repuesto = get_object_or_404(Repuesto, pk=repuesto_id)
        
        MovimientoStock.objects.create(
            repuesto=repuesto,
            tipo=tipo,
            cantidad=cantidad,
            responsable=request.user,
            notas=notas
        )
        
        messages.success(request, f'Movimiento registrado: {tipo} de {cantidad} unidades.')
        return redirect('inventario:detalle_repuesto', pk=repuesto_id)
    
    return render(request, 'inventario_app/registrar_movimiento.html', {
        'repuestos': Repuesto.objects.all()
    })


@login_required
def arbol_categorias(request):
    categorias_padre = Categoria.objects.filter(padre__isnull=True).prefetch_related('subcategorias')
    
    for cat in categorias_padre:
        cat.total_repuestos = Repuesto.objects.filter(categoria=cat).count()
        for subcat in cat.subcategorias.all():
            subcat.total_repuestos = Repuesto.objects.filter(categoria=subcat).count()
    
    return render(request, 'inventario_app/arbol_categorias.html', {
        'categorias_padre': categorias_padre,
    })
import qrcode
import base64
from io import BytesIO

@login_required
def imprimir_etiqueta(request, pk):
    """Genera una etiqueta con código interno y QR para imprimir"""
    repuesto = get_object_or_404(Repuesto, pk=pk)
    
    # Generar código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(repuesto.codigo_interno)
    qr.make(fit=True)
    
    # Crear imagen QR
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64 para mostrar en HTML
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'inventario_app/imprimir_etiqueta.html', {
        'repuesto': repuesto,
        'qr_base64': qr_base64,
    })
from django.contrib.auth.decorators import user_passes_test
from django.forms import modelformset_factory

def es_admin(user):
    """Verifica si el usuario es admin o staff"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@user_passes_test(es_admin)
def gestionar_inventario(request):
    """Lista de repuestos con opciones de editar/eliminar (solo admin)"""
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('q')
    
    repuestos = Repuesto.objects.all()
    
    if categoria_id:
        repuestos = repuestos.filter(categoria_id=categoria_id)
    
    if busqueda:
        repuestos = repuestos.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo_interno__icontains=busqueda) |
            Q(numero_parte_haas__icontains=busqueda)
        )
    
    categorias = Categoria.objects.all()
    
    return render(request, 'inventario_app/gestionar_inventario.html', {
        'repuestos': repuestos,
        'categorias': categorias,
        'categoria_actual': categoria_id,
        'busqueda': busqueda,
    })


@user_passes_test(es_admin)
def crear_repuesto(request):
    """Formulario para crear un nuevo repuesto"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        categoria_id = request.POST.get('categoria')
        numero_parte_haas = request.POST.get('numero_parte_haas', '')
        fabricante = request.POST.get('fabricante', '')
        stock_actual = int(request.POST.get('stock_actual', 0))
        stock_minimo = int(request.POST.get('stock_minimo', 0))
        ubicacion = request.POST.get('ubicacion', '')
        estado = request.POST.get('estado', 'nuevo')
        imagen = request.FILES.get('imagen')
        
        categoria = get_object_or_404(Categoria, pk=categoria_id)
        
        # Crear el repuesto
        repuesto = Repuesto.objects.create(
            nombre=nombre,
            categoria=categoria,
            numero_parte_haas=numero_parte_haas,
            fabricante=fabricante,
            stock_actual=stock_actual,
            stock_minimo=stock_minimo,
            ubicacion=ubicacion,
            estado=estado,
            imagen=imagen,
            creado_por=request.user
        )
        
        # Guardar parámetros técnicos
        param_nombres = request.POST.getlist('param_nombre[]')
        param_valores = request.POST.getlist('param_valor[]')
        param_unidades = request.POST.getlist('param_unidad[]')
        
        for i in range(len(param_nombres)):
            if param_nombres[i]:  # Solo si el nombre no está vacío
                ParametroRepuesto.objects.create(
                    repuesto=repuesto,
                    nombre=param_nombres[i],
                    valor=param_valores[i],
                    unidad=param_unidades[i]
                )
        
        messages.success(request, f'Repuesto {repuesto.codigo_interno} creado exitosamente')
        return redirect('inventario:gestionar_inventario')
    
    categorias = Categoria.objects.all()
    
    return render(request, 'inventario_app/crear_repuesto.html', {
        'categorias': categorias,
    })


@user_passes_test(es_admin)
def editar_repuesto(request, pk):
    """Formulario para editar un repuesto existente"""
    repuesto = get_object_or_404(Repuesto, pk=pk)
    parametros = repuesto.parametros.all()
    
    if request.method == 'POST':
        repuesto.nombre = request.POST.get('nombre')
        repuesto.categoria_id = request.POST.get('categoria')
        repuesto.numero_parte_haas = request.POST.get('numero_parte_haas', '')
        repuesto.fabricante = request.POST.get('fabricante', '')
        repuesto.stock_actual = int(request.POST.get('stock_actual', 0))
        repuesto.stock_minimo = int(request.POST.get('stock_minimo', 0))
        repuesto.ubicacion = request.POST.get('ubicacion', '')
        repuesto.estado = request.POST.get('estado', 'nuevo')
        
        # Actualizar imagen si se subió una nueva
        if request.FILES.get('imagen'):
            repuesto.imagen = request.FILES.get('imagen')
        
        repuesto.save()
        
        # Eliminar parámetros antiguos
        repuesto.parametros.all().delete()
        
        # Guardar nuevos parámetros
        param_nombres = request.POST.getlist('param_nombre[]')
        param_valores = request.POST.getlist('param_valor[]')
        param_unidades = request.POST.getlist('param_unidad[]')
        
        for i in range(len(param_nombres)):
            if param_nombres[i]:
                ParametroRepuesto.objects.create(
                    repuesto=repuesto,
                    nombre=param_nombres[i],
                    valor=param_valores[i],
                    unidad=param_unidades[i]
                )
        
        messages.success(request, f'Repuesto {repuesto.codigo_interno} actualizado')
        return redirect('inventario:gestionar_inventario')
    
    categorias = Categoria.objects.all()
    
    return render(request, 'inventario_app/editar_repuesto.html', {
        'repuesto': repuesto,
        'categorias': categorias,
        'parametros': parametros,
    })


@user_passes_test(es_admin)
def eliminar_repuesto(request, pk):
    """Eliminar un repuesto"""
    repuesto = get_object_or_404(Repuesto, pk=pk)
    
    if request.method == 'POST':
        codigo = repuesto.codigo_interno
        repuesto.delete()
        messages.success(request, f'Repuesto {codigo} eliminado')
        return redirect('inventario:gestionar_inventario')
    
    return render(request, 'inventario_app/eliminar_repuesto.html', {
        'repuesto': repuesto,
    })

@user_passes_test(es_admin)
def gestionar_categorias(request):
    """Lista de categorías con opciones de editar/eliminar (solo admin)"""
    busqueda = request.GET.get('q')
    
    # Obtener categorías padre (sin padre)
    categorias_padre = Categoria.objects.filter(padre__isnull=True)
    
    if busqueda:
        categorias_padre = categorias_padre.filter(
            Q(nombre__icontains=busqueda)
        )
    
    # Contar repuestos y subcategorías para cada categoría
    for cat in categorias_padre:
        cat.total_repuestos = Repuesto.objects.filter(categoria=cat).count()
        cat.subcategorias_list = cat.subcategorias.all()
        for subcat in cat.subcategorias_list:
            subcat.total_repuestos = Repuesto.objects.filter(categoria=subcat).count()
    
    return render(request, 'inventario_app/gestionar_categorias.html', {
        'categorias_padre': categorias_padre,
        'busqueda': busqueda,
    })


@user_passes_test(es_admin)
def crear_categoria(request):
    """Formulario para crear una nueva categoría"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        padre_id = request.POST.get('padre')
        prefijo_codigo = request.POST.get('prefijo_codigo', '').upper()
        
        # Validar que el prefijo no se repita
        if prefijo_codigo and Categoria.objects.filter(prefijo_codigo=prefijo_codigo).exists():
            messages.error(request, f'El prefijo "{prefijo_codigo}" ya está en uso. Usa otro.')
            categorias_padre = Categoria.objects.filter(padre__isnull=True)
            return render(request, 'inventario_app/crear_categoria.html', {
                'categorias_padre': categorias_padre,
            })
        
        padre = None
        if padre_id:
            padre = get_object_or_404(Categoria, pk=padre_id)
        
        Categoria.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            padre=padre,
            prefijo_codigo=prefijo_codigo
        )
        
        messages.success(request, f'Categoría "{nombre}" creada exitosamente')
        return redirect('inventario:gestionar_categorias')
    
    categorias_padre = Categoria.objects.filter(padre__isnull=True)
    
    return render(request, 'inventario_app/crear_categoria.html', {
        'categorias_padre': categorias_padre,
    })


@user_passes_test(es_admin)
def editar_categoria(request, pk):
    """Formulario para editar una categoría existente"""
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        categoria.nombre = request.POST.get('nombre')
        categoria.descripcion = request.POST.get('descripcion', '')
        categoria.prefijo_codigo = request.POST.get('prefijo_codigo', '').upper()
        
        padre_id = request.POST.get('padre')
        if padre_id:
            # Evitar que una categoría sea padre de sí misma
            if int(padre_id) == categoria.pk:
                messages.error(request, 'Una categoría no puede ser padre de sí misma')
                categorias_padre = Categoria.objects.filter(padre__isnull=True)
                return render(request, 'inventario_app/editar_categoria.html', {
                    'categoria': categoria,
                    'categorias_padre': categorias_padre,
                })
            categoria.padre_id = padre_id
        else:
            categoria.padre = None
        
        categoria.save()
        messages.success(request, f'Categoría "{categoria.nombre}" actualizada')
        return redirect('inventario:gestionar_categorias')
    
    categorias_padre = Categoria.objects.filter(padre__isnull=True)
    
    return render(request, 'inventario_app/editar_categoria.html', {
        'categoria': categoria,
        'categorias_padre': categorias_padre,
    })


@user_passes_test(es_admin)
def eliminar_categoria(request, pk):
    """Eliminar una categoría"""
    categoria = get_object_or_404(Categoria, pk=pk)
    
    # Verificar si tiene subcategorías o repuestos
    tiene_subcategorias = categoria.subcategorias.exists()
    tiene_repuestos = Repuesto.objects.filter(categoria=categoria).exists()
    
    if request.method == 'POST':
        if tiene_subcategorias:
            messages.error(request, 'No se puede eliminar una categoría que tiene subcategorías. Elimina primero las subcategorías.')
            return redirect('inventario:gestionar_categorias')
        
        if tiene_repuestos:
            messages.error(request, 'No se puede eliminar una categoría que tiene repuestos asociados. Mueve o elimina primero los repuestos.')
            return redirect('inventario:gestionar_categorias')
        
        nombre = categoria.nombre
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada')
        return redirect('inventario:gestionar_categorias')
    
    return render(request, 'inventario_app/eliminar_categoria.html', {
        'categoria': categoria,
        'tiene_subcategorias': tiene_subcategorias,
        'tiene_repuestos': tiene_repuestos,
    })