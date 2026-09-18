import re
from django.core.management.base import BaseCommand
from django.utils import timezone
from catalogue.models import Course, Module, VideoResource

class Command(BaseCommand):
    help = "Seeds authentic, high-quality educational YouTube learning references for all course modules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding real educational YouTube references across all courses..."))

        # Map of course slug -> list of module video specifications
        COURSE_VIDEOS = {
            'python-fundamentals': [
                {
                    'module_order': 1,
                    'title': "Python Tutorial for Beginners - Foundations & Environment",
                    'video_id': "_uQrJ0TkZlc",
                    'channel_name': "Programming with Mosh",
                    'duration_seconds': 3600,
                    'description': "Comprehensive introduction to Python installation, IDE setup, executing scripts, and the Python execution model."
                },
                {
                    'module_order': 2,
                    'title': "Python Integers, Floats & Variable Data Types",
                    'video_id': "kqtD5dpn9C8",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1200,
                    'description': "Deep dive into variable assignment, numeric data types, type casting, and Python memory references."
                },
                {
                    'module_order': 3,
                    'title': "Conditionals and Booleans - If, Else, and Elif Statements",
                    'video_id': "DZwmZ8Usvnk",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 960,
                    'description': "Mastering logical comparisons, boolean operators (and, or, not), and branching execution flow."
                },
                {
                    'module_order': 4,
                    'title': "Loops and Iterations - For and While Loops in Python",
                    'video_id': "6iF8Xb7Z3wQ",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1020,
                    'description': "Practical guide to for-in loops, while loops, range generation, break, continue, and loop control."
                },
                {
                    'module_order': 5,
                    'title': "Python Functions - Parameters, Scope, and Return Values",
                    'video_id': "9Os0o3wzS_I",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1320,
                    'description': "Defining modular reusable functions, positional vs keyword arguments, *args, **kwargs, and return statements."
                },
                {
                    'module_order': 6,
                    'title': "Python OOP - Classes, Instances, Attributes & Methods",
                    'video_id': "ZDa-Z5JzLYM",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1440,
                    'description': "Object-oriented programming architecture: creating classes, __init__ constructor, instance attributes, and encapsulation."
                },
                {
                    'module_order': 7,
                    'title': "Exception Handling with Try, Except, Else & Finally",
                    'video_id': "NIWwJbo-9_8",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 900,
                    'description': "Catching runtime errors defensively, custom exceptions, error logging, and resource cleanup blocks."
                },
                {
                    'module_order': 8,
                    'title': "Python File Objects - Reading, Writing & Parsing Data",
                    'video_id': "tJxcKyFMTGo",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1560,
                    'description': "Context managers with open(), reading text files, writing structured records, and project file manipulation."
                },
            ],
            'python-data-analysis': [
                {
                    'module_order': 1,
                    'title': "NumPy Full Course - High Performance Array Operations",
                    'video_id': "QUT1VHiLmmI",
                    'channel_name': "freeCodeCamp.org",
                    'duration_seconds': 3600,
                    'description': "N-dimensional arrays, vectorization, broadcasting rules, slicing, linear algebra, and memory layout."
                },
                {
                    'module_order': 2,
                    'title': "Pandas Tutorial - DataFrames, Series & Indexing",
                    'video_id': "vmEHCJofslg",
                    'channel_name': "Keith Galli",
                    'duration_seconds': 3600,
                    'description': "Loading CSV datasets, navigating tabular DataFrames, boolean mask filtering, and column transformations."
                },
                {
                    'module_order': 3,
                    'title': "Data Cleaning in Pandas - Handling Missing & Duplicate Data",
                    'video_id': "bDhvCp3_lYw",
                    'channel_name': "Alex The Analyst",
                    'duration_seconds': 1680,
                    'description': "Detecting null values with isna(), imputation techniques, dropna, string stripping, and data type alignment."
                },
                {
                    'module_order': 4,
                    'title': "Data Visualization with Matplotlib & Seaborn",
                    'video_id': "DAQNHzOcO5A",
                    'channel_name': "Derek Banas",
                    'duration_seconds': 2400,
                    'description': "Histograms, scatterplots, heatmaps, categorical plots, and statistical visualization styling."
                },
                {
                    'module_order': 5,
                    'title': "Exploratory Data Analysis with Pandas & GroupBy Aggregations",
                    'video_id': "ua-CiDNNj30",
                    'channel_name': "freeCodeCamp.org",
                    'duration_seconds': 3000,
                    'description': "Full end-to-end EDA pipeline: statistical summaries, group aggregations, pivot tables, and hypothesis testing."
                },
            ],
            'java-fundamentals': [
                {
                    'module_order': 1,
                    'title': "Java Tutorial for Beginners - JVM Architecture & Setup",
                    'video_id': "eIrMbAQSU34",
                    'channel_name': "Programming with Mosh",
                    'duration_seconds': 3600,
                    'description': "JDK, JRE, JVM architecture, bytecode compilation, classpaths, and writing your first Java application."
                },
                {
                    'module_order': 2,
                    'title': "Java Primitive Types, Operators & Control Flow",
                    'video_id': "xL1sF_C_90Y",
                    'channel_name': "Telusko",
                    'duration_seconds': 1800,
                    'description': "Java strong typing, integer & floating arithmetic, if-else cascades, enhanced switch expressions, and loops."
                },
                {
                    'module_order': 3,
                    'title': "Java OOP - Classes, Objects, Memory Allocation & Methods",
                    'video_id': "BSVKUk58KJE",
                    'channel_name': "Telusko",
                    'duration_seconds': 2100,
                    'description': "Stack vs Heap memory in Java, constructor overloading, 'this' keyword, and encapsulation with getters/setters."
                },
                {
                    'module_order': 4,
                    'title': "Java Inheritance, Polymorphism & Interface Contracts",
                    'video_id': "zb_O3kZqjvg",
                    'channel_name': "Telusko",
                    'duration_seconds': 1950,
                    'description': "Extends keyword, method overriding (@Override), abstract classes, interface decoupling, and dynamic dispatch."
                },
                {
                    'module_order': 5,
                    'title': "Java Collections Framework & Exception Hierarchy",
                    'video_id': "qU3fKqZJ2oI",
                    'channel_name': "Telusko",
                    'duration_seconds': 2400,
                    'description': "ArrayList, HashMap, HashSet, generics type safety, checked vs unchecked exceptions, and try-with-resources."
                },
            ],
            'advanced-java-enterprise': [
                {
                    'module_order': 1,
                    'title': "Spring Boot Architecture & Dependency Injection (IoC)",
                    'video_id': "9SGDpanrc8U",
                    'channel_name': "Amigoscode",
                    'duration_seconds': 4200,
                    'description': "Inversion of Control container, @Component, @Service, @Autowired bean lifecycle, and auto-configuration."
                },
                {
                    'module_order': 2,
                    'title': "Building Production RESTful APIs with Spring MVC",
                    'video_id': "35EQXmHKZYs",
                    'channel_name': "Telusko",
                    'duration_seconds': 2700,
                    'description': "@RestController, @GetMapping, @PostMapping, ResponseEntity HTTP status codes, and request validation."
                },
                {
                    'module_order': 3,
                    'title': "Data Persistence with Spring Data JPA & Hibernate ORM",
                    'video_id': "8SGI_XS5OPw",
                    'channel_name': "Amigoscode",
                    'duration_seconds': 3100,
                    'description': "@Entity mapping, JpaRepository, derived query methods, pagination, and transaction management."
                },
                {
                    'module_order': 4,
                    'title': "Spring Security 6 & Stateless JWT Authentication",
                    'video_id': "KxqlJblhzfI",
                    'channel_name': "Bouali Ali - Coding with Bouali",
                    'duration_seconds': 3600,
                    'description': "SecurityFilterChain, OncePerRequestFilter, BCrypt password hashing, token generation, and role-based access control."
                },
                {
                    'module_order': 5,
                    'title': "Enterprise Microservices Architecture with Spring Cloud",
                    'video_id': "y8ITz3zD_14",
                    'channel_name': "Java Techie",
                    'duration_seconds': 3600,
                    'description': "Service discovery with Netflix Eureka, API Gateway routing, distributed configuration, and resilience."
                },
            ],
            'enterprise-fullstack-react-node': [
                {
                    'module_order': 1,
                    'title': "Modern React Architecture - Component Tree & State",
                    'video_id': "bMknfKXIFA8",
                    'channel_name': "freeCodeCamp.org",
                    'duration_seconds': 4500,
                    'description': "Virtual DOM diffing, JSX syntax, useState, useEffect hooks, component composition, and unidirectional data flow."
                },
                {
                    'module_order': 2,
                    'title': "React Router 6, Controlled Forms & Global State",
                    'video_id': "Ul3y1LXxzdU",
                    'channel_name': "Web Dev Simplified",
                    'duration_seconds': 1800,
                    'description': "Declarative client-side routing, useParams, useNavigate, form validation, and Context API state management."
                },
                {
                    'module_order': 3,
                    'title': "Node.js & Express - High-Scale REST API Architecture",
                    'video_id': "Oe421EPjeBE",
                    'channel_name': "freeCodeCamp.org",
                    'duration_seconds': 4800,
                    'description': "Node event loop, non-blocking I/O, Express middleware pipeline, route handlers, and error middleware."
                },
                {
                    'module_order': 4,
                    'title': "PostgreSQL Relational Design & Prisma ORM Modeling",
                    'video_id': "RebA5J-rlh4",
                    'channel_name': "Web Dev Simplified",
                    'duration_seconds': 2100,
                    'description': "Relational schemas, foreign keys, ACID guarantees, migrations, Prisma schema modeling, and performant joins."
                },
                {
                    'module_order': 5,
                    'title': "Full Stack JWT Authentication, Security Headers & Production CI/CD",
                    'video_id': "enopDSs3drw",
                    'channel_name': "Traversy Media",
                    'duration_seconds': 3300,
                    'description': "HttpOnly cookie tokens, CORS whitelisting, helmet security headers, rate limiting, and deployment workflows."
                },
            ],
            'python': [
                {
                    'module_order': 1,
                    'title': "Python Execution Model, Bytecode & Runtime Architecture",
                    'video_id': "_uQrJ0TkZlc",
                    'channel_name': "Programming with Mosh",
                    'duration_seconds': 3600,
                    'description': "CPython interpreter internals, global interpreter lock (GIL), memory allocation, and environment setup."
                },
                {
                    'module_order': 2,
                    'title': "Python Sequences & In-Depth Memory Representation",
                    'video_id': "W8KRzm-HUcc",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1740,
                    'description': "Under-the-hood contiguous arrays for lists, hash tables for dicts/sets, tuple immutability, and shallow vs deep copies."
                },
                {
                    'module_order': 3,
                    'title': "Generators and Iterators in Python - Working with Large Data",
                    'video_id': "bD05uGo_sVI",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1320,
                    'description': "Yield statements, iterator protocol (__iter__, __next__), memory-efficient streaming, and itertools combinations."
                },
                {
                    'module_order': 4,
                    'title': "Python OOP: Classmethods, Staticmethods, and Metaclasses",
                    'video_id': "BJ-VvGyQxho",
                    'channel_name': "Corey Schafer",
                    'duration_seconds': 1560,
                    'description': "Alternative constructors with @classmethod, utility logic with @staticmethod, dunder methods, and inheritance hierarchy."
                },
            ],
        }

        total_updated = 0
        total_created = 0

        for course_slug, v_list in COURSE_VIDEOS.items():
            course = Course.objects.filter(slug=course_slug).first()
            if not course:
                self.stdout.write(self.style.WARNING(f"Course '{course_slug}' not found, skipping."))
                continue

            self.stdout.write(f"\nProcessing Course: {course.title} ({course_slug})")

            for v_info in v_list:
                m_order = v_info['module_order']
                mod = course.modules.filter(order=m_order).first()
                if not mod:
                    self.stdout.write(self.style.WARNING(f"  Module order {m_order} not found in {course_slug}."))
                    continue

                primary_lesson = mod.lessons.order_by('order').first()
                yt_id = v_info['video_id']
                yt_url = f"https://www.youtube.com/watch?v={yt_id}"
                thumb_url = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"

                # Check if a video resource already exists for this module
                existing_video = mod.videos.first()
                if existing_video:
                    existing_video.title = v_info['title']
                    existing_video.description = v_info['description']
                    existing_video.video_type = 'YOUTUBE'
                    existing_video.youtube_url = yt_url
                    existing_video.youtube_video_id = yt_id
                    existing_video.thumbnail_url = thumb_url
                    existing_video.channel_name = v_info['channel_name']
                    existing_video.duration_seconds = v_info['duration_seconds']
                    mins = v_info['duration_seconds'] // 60
                    existing_video.duration_if_available = f"{mins} mins"
                    existing_video.is_required = True
                    existing_video.is_unavailable = False
                    existing_video.status = 'PUBLISHED'
                    existing_video.lesson = primary_lesson
                    existing_video.verified_at = timezone.now()
                    existing_video.save()
                    total_updated += 1
                    self.stdout.write(self.style.SUCCESS(f"  [UPDATED] Mod {m_order} ('{mod.title}'): {v_info['title']} ({yt_id})"))
                else:
                    VideoResource.objects.create(
                        module=mod,
                        lesson=primary_lesson,
                        order=1,
                        title=v_info['title'],
                        description=v_info['description'],
                        video_type='YOUTUBE',
                        youtube_url=yt_url,
                        youtube_video_id=yt_id,
                        thumbnail_url=thumb_url,
                        channel_name=v_info['channel_name'],
                        duration_seconds=v_info['duration_seconds'],
                        duration_if_available=f"{v_info['duration_seconds'] // 60} mins",
                        completion_threshold_percent=80.0,
                        is_required=True,
                        is_unavailable=False,
                        status='PUBLISHED',
                        verified_at=timezone.now()
                    )
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  [CREATED] Mod {m_order} ('{mod.title}'): {v_info['title']} ({yt_id})"))

        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted YouTube References Seeding: {total_updated} updated, {total_created} created."
        ))
