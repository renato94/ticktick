from database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    Boolean,
    text,
    Double,
    ForeignKey,
)
from sqlalchemy.orm import relationship


class Goal(Base):
    __tablename__ = "goal"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"), onupdate=text("now()"))

    steps = relationship("Step", back_populates="goal")
    # make goal refer it self, so that we can have sub goals
    parent_id = Column(Integer, ForeignKey("goal.id"))
    sub_goals = relationship("Goal")


class Step(Base):
    __tablename__ = "step"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"), onupdate=text("now()"))

    goal_id = Column(Integer, ForeignKey("goal.id"))
    goal = relationship("Goal", back_populates="steps")

    tasks = relationship("Task", back_populates="step")


class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"), onupdate=text("now()"))

    color = Column(String, nullable=True)
    exclude_days = Column(String, nullable=True)
    exclude_weeks = Column(String, nullable=True)
    exclude_months = Column(String, nullable=True)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)

    step_id = Column(Integer, ForeignKey("step.id"))
    step = relationship("Step", back_populates="tasks")
