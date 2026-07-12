"""
所有模型的统一导出入口。
"""
from app.models.user import User
from app.models.position import JobPosition, Skill, SkillChange
from app.models.resume import Resume, Education, WorkExperience, Project
from app.models.match import MatchResult, MatchDimension, GapAnalysis, ImprovementSuggestion
from app.models.learning import LearningPath, LearningStep, LearningResource
from app.models.favorite import Favorite

__all__ = [
    "User",
    "JobPosition", "Skill", "SkillChange",
    "Resume", "Education", "WorkExperience", "Project",
    "MatchResult", "MatchDimension", "GapAnalysis", "ImprovementSuggestion",
    "LearningPath", "LearningStep", "LearningResource",
    "Favorite",
]
