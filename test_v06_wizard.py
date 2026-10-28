"""Compatibility entrypoint for older developers; v0.6.3 supersedes v0.6.

The 0.6 wizard expected a redundant checkbox and is no longer applicable.
Run the active tests instead: test_v063_wizard.py, test_v063_partial_gui.py.
"""
if __name__=='__main__':
    from test_v063_wizard import check_inventory,check_bad_source
    from desktop_app import load_catalog
    ids=[p['id'] for p in load_catalog()[0]['palicoes']]
    check_inventory(ids,'install')
    check_bad_source()
