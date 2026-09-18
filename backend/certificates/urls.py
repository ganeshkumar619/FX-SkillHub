from django.urls import path
from .views import (
    GenerateCertificateView,
    IssueCertificateView,
    DownloadCertificatePDFView,
    CertificateQRCodeView,
    PublicVerifyCertificateView,
    UserCertificatesListView,
    AdminCertificateListView,
    AdminRevokeCertificateView,
    AdminRestoreCertificateView,
    AdminDeleteCertificateView,
    AdminRegenerateCertificateView,
    AdminBrandingView,
    AdminBrandingUploadView,
    AdminCertificateConfigView,
    PublicCertificateConfigView
)

urlpatterns = [
    path('config/', PublicCertificateConfigView.as_view(), name='public_certificate_config'),
    path('generate/', GenerateCertificateView.as_view(), name='generate_certificate'),
    path('issue/', IssueCertificateView.as_view(), name='issue_certificate'),
    path('my/', UserCertificatesListView.as_view(), name='my_certificates'),
    path('<str:certificate_id>/pdf/', DownloadCertificatePDFView.as_view(), name='download_certificate_pdf'),
    path('<str:certificate_id>/qr/', CertificateQRCodeView.as_view(), name='certificate_qr_image'),
    path('verify/<str:certificate_id>/', PublicVerifyCertificateView.as_view(), name='public_verify_certificate'),
    
    # Admin Certificate & Branding Management
    path('admin/', AdminCertificateListView.as_view(), name='admin_certificate_list'),
    path('admin/<uuid:certificate_id>/revoke/', AdminRevokeCertificateView.as_view(), name='admin_revoke_certificate'),
    path('admin/<uuid:certificate_id>/restore/', AdminRestoreCertificateView.as_view(), name='admin_restore_certificate'),
    path('admin/<uuid:certificate_id>/regenerate/', AdminRegenerateCertificateView.as_view(), name='admin_regenerate_certificate'),
    path('admin/<uuid:certificate_id>/delete/', AdminDeleteCertificateView.as_view(), name='admin_delete_certificate'),
    path('admin/<uuid:certificate_id>/', AdminDeleteCertificateView.as_view(), name='admin_delete_certificate_direct'),
    path('admin/branding/', AdminBrandingView.as_view(), name='admin_branding_list'),
    path('admin/branding/upload/', AdminBrandingUploadView.as_view(), name='admin_branding_upload'),
    path('admin/config/', AdminCertificateConfigView.as_view(), name='admin_certificate_config'),
]
