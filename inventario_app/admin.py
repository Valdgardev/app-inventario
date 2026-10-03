from django.contrib import admin
from .models import Categoria, Repuesto, MovimientoStock, ParametroCategoria, ParametroRepuesto


class ParametroRepuestoInline(admin.TabularInline):
    """Permite agregar parámetros directamente en el formulario del repuesto"""
    model = ParametroRepuesto
    extra = 1  # Muestra 1 fila vacía para agregar parámetros
    fields = ['nombre', 'valor', 'unidad']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'padre', 'prefijo_codigo', 'descripcion_corta']
    list_filter = ['padre']
    search_fields = ['nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'padre', 'descripcion')
        }),
        ('Código Automático', {
            'fields': ('prefijo_codigo',),
            'description': 'Este prefijo se usará para generar códigos automáticos. Ej: HID, VAL, ELE'
        }),
    )
    
    def descripcion_corta(self, obj):
        if obj.descripcion:
            return obj.descripcion[:50] + '...'
        return '-'
    descripcion_corta.short_description = 'Descripción'


@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_interno', 
        'nombre', 
        'categoria', 
        'numero_parte_haas',
        'stock_actual', 
        'estado',
        'ubicacion'
    ]
    list_filter = ['categoria', 'estado']
    search_fields = ['codigo_interno', 'nombre', 'numero_parte_haas', 'fabricante']
    list_editable = ['stock_actual', 'estado']
    readonly_fields = ['codigo_interno', 'creado_por', 'fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('📋 Información Básica', {
            'fields': ('nombre', 'codigo_interno', 'categoria', 'imagen')
        }),
        ('🏭 Identificadores del Fabricante', {
            'fields': ('numero_parte_haas', 'fabricante', 'numero_serie')
        }),
        ('📦 Stock y Ubicación', {
            'fields': ('stock_actual', 'stock_minimo', 'ubicacion', 'estado')
        }),
        ('💰 Información de Compra', {
            'fields': ('valor_unitario', 'proveedor_ultima_compra', 'fecha_ultima_compra')
        }),
        ('🔒 Metadata (solo lectura)', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ParametroRepuestoInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'repuesto', 'tipo', 'cantidad', 'responsable']
    list_filter = ['tipo', 'fecha']
    search_fields = ['repuesto__codigo_interno', 'repuesto__nombre', 'notas']
    readonly_fields = ['fecha']
    
    fieldsets = (
        ('📝 Registro de Movimiento', {
            'fields': ('repuesto', 'tipo', 'cantidad', 'responsable', 'notas')
        }),
        ('🕐 Información del Sistema', {
            'fields': ('fecha',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.responsable_id:
            obj.responsable = request.user
        super().save_model(request, obj, form, change)


@admin.register(ParametroCategoria)
class ParametroCategoriaAdmin(admin.ModelAdmin):
    list_display = ['categoria', 'nombre', 'unidad']
    list_filter = ['categoria']
    search_fields = ['nombre']