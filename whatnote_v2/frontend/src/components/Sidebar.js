import React, { useState, useEffect } from 'react';
import './Sidebar.css';

function Sidebar({ 
  courses, 
  selectedCourse, 
  selectedBoard,
  onSelectCourse, 
  onSelectBoard,
  onCreateCourse,
  onCreateBoard 
}) {
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [showCreateBoard, setShowCreateBoard] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDesc, setNewCourseDesc] = useState('');
  const [newBoardName, setNewBoardName] = useState('');
  const [courseBoards, setCourseBoards] = useState({});

  // 获取课程的展板列表
  useEffect(() => {
    const fetchCourseBoards = async () => {
      const boardsData = {};
      for (const course of courses) {
        try {
        const response = await fetch(`http://localhost:8081/api/courses/${course.id}/boards`);
          if (response.ok) {
            const data = await response.json();
            boardsData[course.id] = data.boards || [];
          }
        } catch (error) {
          console.error(`获取课程 ${course.id} 的展板失败:`, error);
          boardsData[course.id] = [];
        }
      }
      setCourseBoards(boardsData);
    };

    if (courses.length > 0) {
      fetchCourseBoards();
    }
  }, [courses]);

  const handleCreateCourse = async () => {
    if (newCourseName.trim()) {
      await onCreateCourse(newCourseName.trim(), newCourseDesc.trim());
      setNewCourseName('');
      setNewCourseDesc('');
      setShowCreateCourse(false);
    }
  };

  const handleCreateBoard = async () => {
    if (newBoardName.trim() && selectedCourse) {
      await onCreateBoard(selectedCourse.id, newBoardName.trim());
      setNewBoardName('');
      setShowCreateBoard(false);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h3>课程管理</h3>
        <button 
          className="create-btn"
          onClick={() => setShowCreateCourse(true)}
        >
          + 新建课程
        </button>
      </div>
      
      <div className="courses-list">
        {courses.map(course => (
          <div 
            key={course.id} 
            className={`course-item ${selectedCourse?.id === course.id ? 'selected' : ''}`}
          >
            <div 
              className="course-header"
              onClick={() => onSelectCourse(course)}
            >
              <span className="course-name">{course.name || '未命名课程'}</span>
              <button 
                className="create-board-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCourse(course);
                  setShowCreateBoard(true);
                }}
              >
                + 展板
              </button>
            </div>
            
            {selectedCourse?.id === course.id && (
              <div className="boards-list">
                {courseBoards[course.id]?.map(board => (
                  <div 
                    key={board.id}
                    className={`board-item ${selectedBoard?.id === board.id ? 'selected' : ''}`}
                    onClick={() => onSelectBoard(board)}
                  >
                    📋 {board.name || '未命名展板'}
                  </div>
                ))}
                {(!courseBoards[course.id] || courseBoards[course.id].length === 0) && (
                  <div className="no-boards">
                    暂无展板
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        
        {courses.length === 0 && (
          <div className="no-courses">
            暂无课程，请创建第一个课程
          </div>
        )}
      </div>
      
      {/* 创建课程弹窗 */}
      {showCreateCourse && (
        <div className="modal-overlay" onClick={() => setShowCreateCourse(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>创建新课程</h3>
            <input
              type="text"
              placeholder="课程名称"
              value={newCourseName}
              onChange={(e) => setNewCourseName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateCourse()}
            />
            <textarea
              placeholder="课程描述（可选）"
              value={newCourseDesc}
              onChange={(e) => setNewCourseDesc(e.target.value)}
            />
            <div className="modal-buttons">
              <button onClick={handleCreateCourse}>创建</button>
              <button onClick={() => setShowCreateCourse(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
      
      {/* 创建展板弹窗 */}
      {showCreateBoard && (
        <div className="modal-overlay" onClick={() => setShowCreateBoard(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>创建新展板</h3>
            <input
              type="text"
              placeholder="展板名称"
              value={newBoardName}
              onChange={(e) => setNewBoardName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateBoard()}
            />
            <div className="modal-buttons">
              <button onClick={handleCreateBoard}>创建</button>
              <button onClick={() => setShowCreateBoard(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Sidebar; 