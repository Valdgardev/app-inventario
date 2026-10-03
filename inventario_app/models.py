from django.db import models
from django.contrib.auth.models import User
from django.db.models import F
from django.db import transaction


class Categoria(models.Model):
    """Categoría y subcategoría de repuestos (jerarquía infinita)"""
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    padre = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE, 
        related_name='subcategorias'
    )
    prefijo_codigo = models.CharField(
        max_length=10, 
        blank=True,
        verbose_name='Prefijo de Código',
        help_text='Ej: HID para Hidráulica, VAL para Válvulas'
    )
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']
    
    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} > {self.nombre}"
        return self.nombre
    
    def obtener_prefijo_completo(self):
        """Obtiene el prefijo completo concatenando padres"""
        if self.padre and self.padre.prefijo_codigo:
            return f"{self.padre.prefijo_codigo}-{self.prefijo_codigo}"
        return self.prefijo_codigo


class Repuesto(models.Model):
    """Repuesto o insumo del inventario"""
    
    # Información básica
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Ítem')
    codigo_interno = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        verbose_name='Código Interno',
        help_text='Se genera automáticamente si se deja vacío'
    )
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.PROTECT,
        verbose_name='Categoría'
    )
    
    # Identificadores del fabricante
    numero_parte_haas = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Nº Parte HAAS',
        help_text='Número de parte asignado por HAAS'
    )
    fabricante = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Nº de Serie',
        help_text='Para herramientas o ítems únicos'
    )
    
    # Información de stock
    stock_actual = models.IntegerField(default=0, verbose_name='Stock Actual')
    stock_minimo = models.IntegerField(default=0, verbose_name='Stock Mínimo')
    ubicacion = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Ubicación Física',
        help_text='Ej: Estante A, Cajón 3'
    )
    estado = models.CharField(
        max_length=50, 
        choices=[
            ('nuevo', 'Nuevo'),
            ('usado', 'Usado (Operativo)'),
            ('malo', 'Malo/Para Reparar')
        ],
        default='nuevo',
        verbose_name='Estado'
    )
    
    # Imagen del repuesto
    imagen = models.ImageField(
        upload_to='repuestos/', 
        blank=True, 
        null=True,
        verbose_name='Imagen'
    )
    
    # Especificaciones técnicas (campo flexible JSON)
    especificaciones = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Especificaciones Técnicas',
        help_text='Ej: {"voltaje": "24V", "hilo": "1/4 NPT"}'
    )
    
    # Información de compra
    valor_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Valor Unitario (CLP)'
    )
    proveedor_ultima_compra = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name='Proveedor Última Compra'
    )
    fecha_ultima_compra = models.DateField(
        null=True, 
        blank=True,
        verbose_name='Fecha Última Compra'
    )
    
    # Metadata
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='repuestos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Repuesto'
        verbose_name_plural = 'Repuestos'
        ordering = ['categoria', 'nombre']
    
    def __init__(self, *args, **kwargs):
        """Guardamos la categoría original al cargar el objeto de la base de datos"""
        super().__init__(*args, **kwargs)
        self._original_categoria_id = self.categoria_id
    
    def __str__(self):
        return f"{self.codigo_interno} - {self.nombre}"
    
    @property
    def necesita_reabastecimiento(self):
        """Retorna True si el stock está por debajo del mínimo"""
        return self.stock_actual <= self.stock_minimo
    
    def save(self, *args, **kwargs):
        """Genera o regenera el código si es nuevo o si cambió la categoría"""
        
        # Condición: Es un repuesto nuevo (sin pk) O la categoría cambió
        if not self.pk or (self.pk and self._original_categoria_id != self.categoria_id):
            if self.categoria:
                prefijo = self.categoria.obtener_prefijo_completo()
                
                if prefijo:
                    # Buscamos el último repuesto con este prefijo
                    queryset = Repuesto.objects.filter(codigo_interno__startswith=f"{prefijo}-")
                    
                    # Si estamos editando, excluimos este mismo repuesto de la búsqueda
                    if self.pk:
                        queryset = queryset.exclude(pk=self.pk)
                    
                    ultimo_repuesto = queryset.order_by('-codigo_interno').first()
                    
                    if ultimo_repuesto:
                        ultimo_numero = int(ultimo_repuesto.codigo_interno.split('-')[-1])
                        nuevo_numero = ultimo_numero + 1
                    else:
                        nuevo_numero = 1
                    
                    self.codigo_interno = f"{prefijo}-{str(nuevo_numero).zfill(4)}"
        
        # Guardamos el objeto en la base de datos
        super().save(*args, **kwargs)
        
        # Actualizamos el valor original después de guardar para futuras ediciones
        self._original_categoria_id = self.categoria_id


class MovimientoStock(models.Model):
    """Registro de entradas y salidas de stock"""
    
    repuesto = models.ForeignKey(
        Repuesto, 
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name='Repuesto'
    )
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('entrada', 'Entrada (Compra/Devolución)'),
            ('salida', 'Salida (Uso en terreno)'),
            ('ajuste', 'Ajuste de Inventario')
        ],
        verbose_name='Tipo de Movimiento'
    )
    cantidad = models.IntegerField(verbose_name='Cantidad')
    responsable = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Responsable'
    )
    notas = models.TextField(blank=True, verbose_name='Notas')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y Hora')
    
    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.repuesto.codigo_interno} ({self.cantidad})"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        """Actualiza el stock automáticamente de forma segura (atómica)"""
        # 1. Guardamos el movimiento primero en la base de datos
        super().save(*args, **kwargs)
        
        # 2. Actualizamos el stock de forma atómica (evita que 2 usuarios lo pisoteen)
        if self.tipo == 'entrada':
            Repuesto.objects.filter(pk=self.repuesto_id).update(stock_actual=F('stock_actual') + self.cantidad)
        elif self.tipo == 'salida':
            Repuesto.objects.filter(pk=self.repuesto_id).update(stock_actual=F('stock_actual') - self.cantidad)
        elif self.tipo == 'ajuste':
            Repuesto.objects.filter(pk=self.repuesto_id).update(stock_actual=self.cantidad)
        
        # 3. Refrescamos el objeto en memoria por si se usa después en el código
        self.repuesto.refresh_from_db()
        
    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.repuesto.codigo_interno} ({self.cantidad})"
    
    def save(self, *args, **kwargs):
        """Actualiza el stock automáticamente al guardar un movimiento"""
        super().save(*args, **kwargs)
        
        if self.tipo == 'entrada':
            self.repuesto.stock_actual += self.cantidad
        elif self.tipo == 'salida':
            self.repuesto.stock_actual -= self.cantidad
        elif self.tipo == 'ajuste':
            self.repuesto.stock_actual = self.cantidad
        
        self.repuesto.save()


class ParametroCategoria(models.Model):
    """Define qué parámetros técnicos aplican a cada categoría (plantilla)"""
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.CASCADE,
        related_name='parametros_definidos'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre del Parámetro',
        help_text='Ej: Voltaje, Medida Interior, Capacitancia'
    )
    unidad = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Unidad de Medida',
        help_text='Ej: V, mm, µF, PSI, metros'
    )
    
    class Meta:
        verbose_name = 'Parámetro de Categoría'
        verbose_name_plural = 'Parámetros de Categoría'
        unique_together = ['categoria', 'nombre']
        ordering = ['categoria', 'nombre']
    
    def __str__(self):
        if self.unidad:
            return f"{self.nombre} ({self.unidad})"
        return self.nombre


class ParametroRepuesto(models.Model):
    """Parámetros técnicos específicos de cada repuesto"""
    repuesto = models.ForeignKey(
        Repuesto, 
        on_delete=models.CASCADE,
        related_name='parametros'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre del Parámetro'
    )
    valor = models.CharField(
        max_length=200,
        verbose_name='Valor'
    )
    unidad = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Unidad de Medida'
    )
    
    class Meta:
        verbose_name = 'Parámetro del Repuesto'
        verbose_name_plural = 'Parámetros del Repuesto'
        ordering = ['nombre']
    
    def __str__(self):
        if self.unidad:
            return f"{self.nombre}: {self.valor} {self.unidad}"
        return f"{self.nombre}: {self.valor}"