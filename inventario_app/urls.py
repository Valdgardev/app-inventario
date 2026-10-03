from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('stock/', views.lista_repuestos, name='lista_repuestos'),
    path('stock/<int:pk>/', views.detalle_repuesto, name='detalle_repuesto'),
    path('stock/movimiento/nuevo/', views.registrar_movimiento, name='registrar_movimiento'),
    path('categorias/', views.arbol_categorias, name='arbol_categorias'),
    path('stock/<int:pk>/etiqueta/', views.imprimir_etiqueta, name='imprimir_etiqueta'),
    # Nuevas rutas de gestión (solo admin)
    path('gestionar/', views.gestionar_inventario, name='gestionar_inventario'),
    path('gestionar/crear/', views.crear_repuesto, name='crear_repuesto'),
    path('gestionar/<int:pk>/editar/', views.editar_repuesto, name='editar_repuesto'),
    path('gestionar/<int:pk>/eliminar/', views.eliminar_repuesto, name='eliminar_repuesto'),
    path('categorias/gestionar/', views.gestionar_categorias, name='gestionar_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),

]