from rest_framework import serializers
from .models import (
    Department, 
    SkillCategory, 
    SkillDomain, 
    Skill, 
    Course, 
    Module, 
    Lesson, 
    LearningResource,
    VideoResource,
    StudyMaterial,
    PracticeTask,
    CourseApproval,
    CourseVersion,
    AISkillSuggestion,
    StudentSkillProfile,
    SkillRecommendation,
    CourseRecommendation
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class SkillDomainSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SkillDomain
        fields = '__all__'


class SkillCategorySerializer(serializers.ModelSerializer):
    domains = SkillDomainSerializer(many=True, read_only=True)

    class Meta:
        model = SkillCategory
        fields = '__all__'


class SkillSerializer(serializers.ModelSerializer):
    category = SkillCategorySerializer(read_only=True)
    domain = SkillDomainSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    departments = DepartmentSerializer(many=True, read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=SkillCategory.objects.all(), source='category', write_only=True
    )
    domain_id = serializers.PrimaryKeyRelatedField(
        queryset=SkillDomain.objects.all(), source='domain', write_only=True, required=False, allow_null=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Skill
        fields = '__all__'


class VideoResourceSerializer(serializers.ModelSerializer):
    embed_url = serializers.CharField(source='get_embed_url', read_only=True)

    class Meta:
        model = VideoResource
        fields = '__all__'


class StudyMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyMaterial
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        sc = data.get('structured_content')
        if isinstance(sc, dict) and 'common_mistakes' in sc:
            normalized_cms = []
            for item in sc.get('common_mistakes', []):
                if isinstance(item, dict):
                    pitfall = (item.get('common_pitfall') or item.get('mistake') or '').strip()
                    solution = (item.get('recommended_solution') or item.get('correct') or item.get('good_code') or item.get('resolution') or '').strip()
                    rationale = (item.get('technical_rationale') or item.get('reason') or item.get('explanation') or '').strip()
                    normalized_item = dict(item)
                    normalized_item['common_pitfall'] = pitfall
                    normalized_item['recommended_solution'] = solution
                    normalized_item['technical_rationale'] = rationale
                    normalized_item['mistake'] = pitfall
                    normalized_item['correct'] = solution
                    normalized_item['reason'] = rationale
                    normalized_cms.append(normalized_item)
            data['structured_content']['common_mistakes'] = normalized_cms
        return data


class PracticeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeTask
        fields = '__all__'


class LearningResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = '__all__'


class LessonSerializer(serializers.ModelSerializer):
    videos = VideoResourceSerializer(many=True, read_only=True)
    materials = StudyMaterialSerializer(many=True, read_only=True)
    practice_tasks = PracticeTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        cms = data.get('common_mistakes')
        if isinstance(cms, list):
            normalized_cms = []
            for item in cms:
                if isinstance(item, dict):
                    pitfall = (item.get('common_pitfall') or item.get('mistake') or '').strip()
                    solution = (item.get('recommended_solution') or item.get('correct') or item.get('good_code') or item.get('resolution') or '').strip()
                    rationale = (item.get('technical_rationale') or item.get('reason') or item.get('explanation') or '').strip()
                    normalized_item = dict(item)
                    normalized_item['common_pitfall'] = pitfall
                    normalized_item['recommended_solution'] = solution
                    normalized_item['technical_rationale'] = rationale
                    normalized_item['mistake'] = pitfall
                    normalized_item['correct'] = solution
                    normalized_item['reason'] = rationale
                    normalized_cms.append(normalized_item)
            data['common_mistakes'] = normalized_cms
        return data


class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    resources = LearningResourceSerializer(many=True, read_only=True)
    videos = VideoResourceSerializer(many=True, read_only=True)
    materials = StudyMaterialSerializer(many=True, read_only=True)
    practice_tasks = PracticeTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = '__all__'


class CourseListSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    departments = DepartmentSerializer(many=True, read_only=True)
    modules_count = serializers.IntegerField(source='modules.count', read_only=True)

    class Meta:
        model = Course
        fields = '__all__'


class CourseDetailSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    departments = DepartmentSerializer(many=True, read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)
    prerequisites = CourseListSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = '__all__'


class CourseApprovalSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)

    class Meta:
        model = CourseApproval
        fields = '__all__'


class CourseVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseVersion
        fields = '__all__'


class AISkillSuggestionSerializer(serializers.ModelSerializer):
    department_code = serializers.CharField(source='department.code', read_only=True)

    class Meta:
        model = AISkillSuggestion
        fields = '__all__'


class StudentSkillProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentSkillProfile
        fields = '__all__'


class SkillRecommendationSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)

    class Meta:
        model = SkillRecommendation
        fields = '__all__'


class CourseRecommendationSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = CourseRecommendation
        fields = '__all__'
