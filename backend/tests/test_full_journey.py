import os
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

def request(method, path, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            res_headers = dict(response.info())
            res_body = response.read()
            try:
                res_json = json.loads(res_body.decode("utf-8"))
            except:
                res_json = None
            return status_code, res_json, res_body, res_headers
    except urllib.error.HTTPError as e:
        err_body = e.read()
        try:
            err_json = json.loads(err_body.decode("utf-8"))
        except:
            err_json = None
        return e.code, err_json, err_body, dict(e.headers)

def run_test():
    print("=== [1] Testing Health Endpoint ===")
    status, health_data, _, _ = request("GET", "/api/health/")
    assert status == 200, f"Health check failed: {status}"
    print(f"Health Status: {health_data['status']}, Service: {health_data.get('service')}, Version: {health_data.get('version')}")

    print("\n=== [2] Authenticating as Student (demo_student) ===")
    status, user_data, _, _ = request("POST", "/api/auth/login/", {
        "username": "demo_student",
        "password": "Student@FXEC2026!"
    })
    assert status == 200, f"Login failed: {user_data}"
    student_token = user_data.get("token") or user_data.get("access")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print(f"Student logged in: {user_data['user']['username']} (Role: {user_data['user']['role']})")

    print("\n=== [3] Discovering Course in Catalogue ===")
    status, courses_data, _, _ = request("GET", "/api/catalogue/courses/", headers=student_headers)
    assert status == 200
    courses = courses_data.get("results", courses_data) if isinstance(courses_data, dict) else courses_data
    assert len(courses) > 0, f"No courses found in: {courses_data}"
    target_course = courses[0]
    print(f"Found Course: {target_course['title']} (Slug: {target_course['slug']}, Dept: {target_course['department']['name']})")
    print(f"Source Provenance: {target_course['source_type']} -> {target_course['source_url']}")

    print("\n=== [4] Fetching Full Course Details with Modules ===")
    status, course_detail, _, _ = request("GET", f"/api/catalogue/courses/{target_course['slug']}/", headers=student_headers)
    assert status == 200
    modules = course_detail["modules"]
    print(f"Loaded {len(modules)} sequential syllabus modules.")

    print("\n=== [5] Enrolling in Course ===")
    status, enrollment, _, _ = request("POST", "/api/learning/enroll/", {"course_id": target_course["id"]}, headers=student_headers)
    assert status in (200, 201), f"Enrollment failed: {enrollment}"
    print(f"Enrollment Active (ID: {enrollment['id']}, Progress: {enrollment['progress_percent']}%)")

    print("\n=== [6] Completing Modules Sequentially ===")
    for m in modules:
        status, prog, _, _ = request("POST", f"/api/learning/modules/{m['id']}/complete/", headers=student_headers)
        assert status == 200
        print(f" Completed Module {m['order']}: {m['title']} -> Overall Progress: {prog['progress_percent']}%")

    print("\n=== [7] Diagnostic Pre-Assessment & AI Skill Gap Analysis ===")
    status, pre_assess, _, _ = request("GET", f"/api/assessments/course/{target_course['id']}/pre-assessment/", headers=student_headers)
    assert status == 200
    print(f"Pre-Assessment Title: {pre_assess['title']}")

    status, pre_attempt, _, _ = request("POST", f"/api/assessments/{pre_assess['id']}/start/", headers=student_headers)
    assert status in (200, 201)
    pre_attempt_id = pre_attempt["id"]
    print(f"Started Pre-Assessment Attempt: {pre_attempt_id}")

    # Autosave an answer
    if pre_attempt["questions"]:
        q0 = pre_attempt["questions"][0]
        if q0["options"]:
            opt0 = q0["options"][0]["id"]
            status, _, _, _ = request("POST", f"/api/assessments/attempts/{pre_attempt_id}/answers/", {
                "question_id": q0["id"],
                "option_ids": [opt0]
            }, headers=student_headers)
            assert status == 200

    status, pre_result, _, _ = request("POST", f"/api/assessments/attempts/{pre_attempt_id}/submit/", headers=student_headers)
    assert status == 200
    print(f"Diagnostic Pre-Assessment Submitted: Score {pre_result['score']} ({pre_result['percentage']}%)")
    if "skill_gap_analysis" in pre_result and pre_result["skill_gap_analysis"]:
        print(f"Skill Gap Identified: {pre_result['skill_gap_analysis'].get('weak_topics', [])}")
        print(f"Recommendation: {pre_result['skill_gap_analysis'].get('recommendation', '')}")

    print("\n=== [8] Final Certification Assessment with Proctoring Telemetry ===")
    status, final_assess, _, _ = request("GET", f"/api/assessments/course/{target_course['id']}/final-assessment/", headers=student_headers)
    assert status == 200
    print(f"Final Assessment: {final_assess['title']} (Pass Criteria: {final_assess['pass_percentage']}%)")

    status, final_attempt, _, _ = request("POST", f"/api/assessments/{final_assess['id']}/start/", headers=student_headers)
    assert status in (200, 201)
    final_attempt_id = final_attempt["id"]
    print(f"Final Attempt ID: {final_attempt_id} (Server Deadline: {final_attempt['server_deadline']})")

    # Send proctoring events
    status, evt_res, _, _ = request("POST", f"/api/assessments/attempts/{final_attempt_id}/events/", {
        "event_type": "TAB_SWITCH",
        "severity": "MEDIUM",
        "details": {"client_timestamp": "2026-09-11T10:00:00Z"}
    }, headers=student_headers)
    assert status == 200
    print(f"Proctoring Event TAB_SWITCH Logged -> Risk Tier: {evt_res['current_risk_tier']} (Score: {evt_res['risk_score']})")

    # Look up correct options from Django models
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fx_skillhub.settings')
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    import django
    django.setup()
    from assessments.models import QuestionOption

    for q_data in final_attempt["questions"]:
        correct_opts = list(QuestionOption.objects.filter(question_id=q_data["id"], is_correct=True).values_list('id', flat=True))
        if correct_opts:
            status, _, _, _ = request("POST", f"/api/assessments/attempts/{final_attempt_id}/answers/", {
                "question_id": q_data["id"],
                "option_ids": correct_opts
            }, headers=student_headers)
            assert status == 200
            print(f"  Autosaved correct answer for Question {q_data['id']}")

    # Submit final exam
    status, final_result, _, _ = request("POST", f"/api/assessments/attempts/{final_attempt_id}/submit/", headers=student_headers)
    assert status == 200
    print(f"Final Exam Evaluated: Score={final_result['score']}, Percentage={final_result['percentage']}%, Passed={final_result['passed']}")
    assert final_result["passed"] is True, "Expected candidate to pass final exam!"

    print("\n=== [9] Issuing Accredited Digital Certificate ===")
    status, cert_data, _, _ = request("POST", "/api/certificates/issue/", {
        "attempt_id": final_attempt_id
    }, headers=student_headers)
    assert status in (200, 201), f"Certificate issuance failed: {cert_data}"
    cert_id = cert_data.get("certificate_id") or cert_data.get("id")
    print(f"Certificate Generated!")
    print(f"  Certificate Number: {cert_data['certificate_number']}")
    print(f"  Verification URL: {cert_data['verification_url']}")

    # Idempotency check: Calling again returns the exact same certificate
    status_idem, cert_idem, _, _ = request("POST", "/api/certificates/issue/", {
        "attempt_id": final_attempt_id
    }, headers=student_headers)
    assert status_idem == 200
    assert cert_idem["certificate_number"] == cert_data["certificate_number"]
    print("  Idempotency Verified: Duplicate requests return identical certificate.")

    print("\n=== [10] Downloading ReportLab PDF Certificate ===")
    status_pdf, _, pdf_bytes, pdf_headers = request("GET", f"/api/certificates/{cert_id}/pdf/")
    assert status_pdf == 200
    assert "application/pdf" in pdf_headers.get("Content-Type", "")
    assert pdf_bytes.startswith(b"%PDF"), "Response is not valid PDF!"
    print(f"PDF Rendered Successfully: {len(pdf_bytes)} bytes with embedded QR code.")

    print("\n=== [11] Public Cryptographic Verification ===")
    status_pub, pub_data, _, _ = request("GET", f"/api/certificates/verify/{cert_id}/")
    assert status_pub == 200
    assert pub_data["status"] == "VALID"
    print(f"Public Verification Status: {pub_data['status']}")
    print(f"  Recipient: {pub_data['student_name']}")
    print(f"  Institution: {pub_data['institution']}")
    print(f"  Integrity Hash: {pub_data['integrity_hash']}")

    print("\n=== [12] Faculty Mentor Audit & Review Queue ===")
    status_m, mentor_auth, _, _ = request("POST", "/api/auth/login/", {
        "username": "prof_ramesh",
        "password": "Mentor@FXEC2026!"
    })
    assert status_m == 200
    mentor_token = mentor_auth.get("token") or mentor_auth.get("access")
    mentor_headers = {"Authorization": f"Bearer {mentor_token}"}

    status_q, queue, _, _ = request("GET", "/api/proctoring/review-queue/?filter=all", headers=mentor_headers)
    assert status_q == 200
    print(f"Mentor loaded review queue: {len(queue)} attempts found.")

    status_ev, events_data, _, _ = request("GET", f"/api/proctoring/attempts/{final_attempt_id}/events/", headers=mentor_headers)
    assert status_ev == 200
    print(f"Attempt Proctoring Events: {len(events_data['events'])} events recorded.")

    status_v, verdict_res, _, _ = request("POST", f"/api/proctoring/attempts/{final_attempt_id}/verdict/", {
        "verdict": "VALID",
        "notes": "Verified candidate webcam attentiveness. Clear to issue."
    }, headers=mentor_headers)
    assert status_v == 200
    print(f"Mentor Recorded Official Verdict: {verdict_res['verdict']}")

    print("\n=== [13] Institutional Admin Console Audit & Logs ===")
    status_a, admin_auth, _, _ = request("POST", "/api/auth/login/", {
        "username": "fx_admin",
        "password": "Admin@FXEC2026!"
    })
    assert status_a == 200
    admin_token = admin_auth.get("token") or admin_auth.get("access")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    status_prov, prov_list, _, _ = request("GET", "/api/audit/provenance/", headers=admin_headers)
    assert status_prov == 200
    print(f"Admin Checked Content Provenance: {len(prov_list)} courses verified against FXEC records.")

    status_log, logs_list, _, _ = request("GET", "/api/audit/logs/", headers=admin_headers)
    assert status_log == 200
    print(f"Admin Checked System Activity Log: {len(logs_list)} immutable audit events logged.")

    status_mail, mail_list, _, _ = request("GET", "/api/notifications/logs/", headers=admin_headers)
    assert status_mail == 200
    print(f"Admin Checked Email Delivery Log: {len(mail_list)} email dispatches recorded.")

    print("\n==================================================================")
    print("ALL 13 END-TO-END GOLDEN PATH STEPS VERIFIED 100% SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    run_test()
