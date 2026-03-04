def user_role(request):
    """
    Context processor to add user role info to all templates.
    """
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            return {
                'user_role': profile.role,
                'can_edit': profile.can_edit,
                'can_add_visit': profile.can_add_visit,
                'is_dev': profile.is_dev,
                'is_coordonnateur': profile.is_coordonnateur,
                'is_militant': profile.is_militant,
            }
    return {
        'user_role': None,
        'can_edit': False,
        'can_add_visit': False,
        'is_dev': False,
        'is_coordonnateur': False,
        'is_militant': False,
    }
