$ErrorActionPreference = "Stop"

$root = "C:\Users\Owner\nova"

Write-Host ""
Write-Host "NOVA ADMIN RELEASE CHECK"
Write-Host "Root: $root"
Write-Host ""

Set-Location $root

python -m py_compile "$root\app.py"

$code = @"
from app import app

def check(condition, label):
    if not condition:
        raise AssertionError(label)

print("Registered admin routes:")
routes = sorted([str(rule) for rule in app.url_map.iter_rules() if str(rule).startswith("/admin")])
for route in routes:
    print(" -", route)

check("/admin" in routes, "Missing /admin route")
check("/admin/leads" in routes, "Missing /admin/leads route")
check("/admin/leads.csv" in routes, "Missing /admin/leads.csv route")

public_client = app.test_client()
public_admin = public_client.get("/admin")
print("/admin without login ->", public_admin.status_code)
check(public_admin.status_code in (302, 403), "/admin should be protected without login")

client = app.test_client()
client.get("/richard-login")

admin = client.get("/admin")
admin_text = admin.get_data(as_text=True)
print("/admin ->", admin.status_code, "|", admin.content_type, "|", len(admin_text))
check(admin.status_code == 200, "/admin did not return 200")
check("Nova Admin" in admin_text, "/admin missing Nova Admin")
check("Recent leads" in admin_text, "/admin missing Recent leads")
check("/admin/leads" in admin_text, "/admin missing leads link")

leads = client.get("/admin/leads")
leads_text = leads.get_data(as_text=True)
print("/admin/leads ->", leads.status_code, "|", leads.content_type, "|", len(leads_text))
check(leads.status_code == 200, "/admin/leads did not return 200")
check("Nova Leads" in leads_text, "/admin/leads missing Nova Leads")
check("Admin dashboard" in leads_text, "/admin/leads missing dashboard link")
check("Export CSV" in leads_text, "/admin/leads missing Export CSV")
check("Lead filters" in leads_text, "/admin/leads missing filters")

filtered = client.get("/admin/leads?q=Richard&kind=contact&limit=100")
filtered_text = filtered.get_data(as_text=True)
print("/admin/leads filtered ->", filtered.status_code, "|", len(filtered_text))
check(filtered.status_code == 200, "/admin/leads filtered did not return 200")
check("Lead filters" in filtered_text, "/admin/leads filtered missing filters")
check(("Richard Test" in filtered_text) or ("Showing" in filtered_text), "/admin/leads filtered did not render expected body")

csv_response = client.get("/admin/leads.csv?q=Richard&kind=contact&limit=100")
csv_text = csv_response.get_data(as_text=True)
csv_disposition = csv_response.headers.get("Content-Disposition", "")
print("/admin/leads.csv filtered ->", csv_response.status_code, "|", csv_response.content_type, "|", csv_disposition)
check(csv_response.status_code == 200, "/admin/leads.csv did not return 200")
check("created_at,kind,status,name,email,interest,message,source,owner_notes,admin_updated_at" in csv_text, "/admin/leads.csv missing header")
check("attachment;" in csv_disposition, "/admin/leads.csv missing attachment header")

empty_csv = client.get("/admin/leads.csv?q=NO_MATCH_12345&kind=contact&limit=100")
empty_csv_text = empty_csv.get_data(as_text=True)
print("/admin/leads.csv empty filter ->", empty_csv.status_code, "|", len(empty_csv_text))
check(empty_csv.status_code == 200, "/admin/leads.csv empty filter did not return 200")
check("created_at,kind,status,name,email,interest,message,source,owner_notes,admin_updated_at" in empty_csv_text, "/admin/leads.csv empty filter missing header")
check("Richard Test" not in empty_csv_text, "/admin/leads.csv empty filter leaked non-matching lead")

print("")

print("")
print("Checking owner-only admin pills...")

owner_home = client.get("/nova-home-preview")
owner_home_text = owner_home.get_data(as_text=True)
print("/nova-home-preview owner admin pill ->", owner_home.status_code, "|", len(owner_home_text))
check(owner_home.status_code == 200, "/nova-home-preview owner did not return 200")
check("Open Nova admin dashboard" in owner_home_text, "/nova-home-preview missing owner admin pill after login")
check('href="/admin"' in owner_home_text, "/nova-home-preview owner admin pill missing /admin href")

owner_contact = client.get("/contact")
owner_contact_text = owner_contact.get_data(as_text=True)
print("/contact owner admin pill ->", owner_contact.status_code, "|", len(owner_contact_text))
check(owner_contact.status_code == 200, "/contact owner did not return 200")
check("Open Nova admin dashboard" in owner_contact_text, "/contact missing owner admin pill after login")
check('href="/admin"' in owner_contact_text, "/contact owner admin pill missing /admin href")

public_contact = public_client.get("/contact")
public_contact_text = public_contact.get_data(as_text=True)
print("/contact public admin pill hidden ->", public_contact.status_code, "|", len(public_contact_text))
check(public_contact.status_code == 200, "/contact public did not return 200")
check("Open Nova admin dashboard" not in public_contact_text, "/contact leaked owner admin pill to public visitor")
# NOVA_ADMIN_RELEASE_CHECK_OWNER_PILLS_20260709

print("NOVA ADMIN RELEASE CHECK PASSED")
"@

$code | python -

Write-Host ""
Write-Host "Checking staged files for accidental mobile changes..."
$mobileStaged = git diff --cached --name-only | Select-String -Pattern "mobile"

if ($mobileStaged) {
    Write-Host ""
    Write-Host "FAILED: staged mobile files detected:"
    $mobileStaged
    exit 1
}

Write-Host ""
Write-Host "Current git status:"
git status --short

Write-Host ""
Write-Host "NOVA ADMIN RELEASE CHECK PASSED"

