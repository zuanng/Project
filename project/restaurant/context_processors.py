from .cart import Cart


def cart(request):
    """Làm cho cart có thể truy cập từ mọi template"""
    return {"cart": Cart(request)}
