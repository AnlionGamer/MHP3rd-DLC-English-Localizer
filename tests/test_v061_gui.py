"""Legacy compatibility entrypoint: responsive wizard smoke with current step-2 probing."""
if __name__=='__main__':
    from test_v063_wizard import check_inventory
    from desktop_app import load_catalog
    ids=[p['id'] for p in load_catalog()[0]['palicoes']]
    for size in ((760,540),(860,630),(1080,760),(1470,850)):
        check_inventory(ids,'install',size)
