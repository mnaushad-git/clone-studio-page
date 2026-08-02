"""Admin Portal API endpoints, mounted under /api/v1/admin (see router.py in this
package). Every route except auth.login/auth.refresh requires an authenticated admin
session (app/api/deps/admin_auth.py:get_current_admin), enforced at the router level.
"""

from __future__ import annotations
