from rest_framework import serializers
from .models import (
    Enrollment, 
    ModuleProgress, 
    VideoProgress, 
    MaterialProgress, 
    ReportedVideoIssue,
    Quiz, 
    QuizAttempt
)
from catalogue.serializers import CourseListSerializer

class ModuleProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleProgress
        fields = '__all__'


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = '__all__'


class MaterialProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialProgress
        fields = '__all__'


class ReportedVideoIssueSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)
    module_title = serializers.CharField(source='video.module.title', read_only=True)
    course_title = serializers.CharField(source='video.module.course.title', read_only=True)

    class Meta:
        model = ReportedVideoIssue
        fields = '__all__'


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    module_progress = ModuleProgressSerializer(many=True, read_only=True)
    video_progress = VideoProgressSerializer(many=True, read_only=True)
    material_progress = MaterialProgressSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'course', 'enrolled_at',
            'completed_at', 'is_completed', 'progress_percent',
            'is_demo', 'module_progress', 'video_progress', 'material_progress'
        ]
        read_only_fields = ['id', 'student', 'enrolled_at', 'completed_at', 'progress_percent']
