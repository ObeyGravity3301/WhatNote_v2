import React, { useEffect, useMemo, useRef, useState } from 'react';
import './PersonalizationPanel.css';

const formatDate = (isoString) => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date
      .getDate()
      .toString()
      .padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date
      .getMinutes()
      .toString()
      .padStart(2, '0')}`;
  } catch (err) {
    return isoString;
  }
};

const PersonalizationPanel = ({
  boardId,
  boardName,
  settings,
  onRefresh,
}) => {
  const defaultFileInputRef = useRef(null);
  const boardFileInputRef = useRef(null);

  const [uploadingDefault, setUploadingDefault] = useState(false);
  const [uploadingBoard, setUploadingBoard] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('info');
  const [boardDisplayMode, setBoardDisplayMode] = useState('fit');
  const [defaultDisplayMode, setDefaultDisplayMode] = useState('fit');

  const displayModes = settings?.displayModes || [];

  useEffect(() => {
    if (settings) {
      const defaultMode = settings.defaultDisplayMode || 'fit';
      setDefaultDisplayMode(defaultMode);
      setBoardDisplayMode(settings.boardDisplayMode || defaultMode);
    }
  }, [settings]);

  const appliedSummary = useMemo(() => {
    if (!settings || !settings.appliedWallpaper) {
      return '当前使用：纯色桌面 (Win98 默认蓝)';
    }
    const { type, originalName } = settings.appliedWallpaper;
    if (type === 'board') {
      return `当前使用：展板自定义壁纸 (${originalName || '未命名文件'})`;
    }
    if (type === 'default') {
      return `当前使用：全局默认壁纸 (${settings.appliedWallpaper.originalName || '未命名文件'})`;
    }
    return '当前使用：纯色桌面 (Win98 默认蓝)';
  }, [settings]);

  const showStatus = (message, type = 'info') => {
    setStatusMessage(message);
    setStatusType(type);
    if (message) {
      setTimeout(() => {
        setStatusMessage('');
      }, 4000);
    }
  };

  const handleBoardDisplayModeChange = async (event) => {
    const mode = event.target.value;
    setBoardDisplayMode(mode);
    const result = await handleSelectWallpaper(settings?.selectedBoardWallpaperId ?? null, {
      showToast: false,
      displayMode: mode,
    });
    if (result) {
      showStatus('壁纸显示模式已更新。', 'success');
    }
  };

  const handleDefaultDisplayModeChange = async (event) => {
    const mode = event.target.value;
    setDefaultDisplayMode(mode);
    showStatus('正在更新默认壁纸显示模式...', 'info');
    try {
      const response = await fetch('http://localhost:8081/api/personalization/wallpapers/default/display-mode', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ displayMode: mode }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || '设置失败');
      }

      const latest = await onRefresh?.();
      if (latest) {
        setDefaultDisplayMode(latest.defaultDisplayMode || 'fit');
        setBoardDisplayMode(latest.boardDisplayMode || latest.defaultDisplayMode || 'fit');
      }
      showStatus('默认壁纸显示模式已更新。', 'success');
    } catch (error) {
      console.error('更新默认壁纸显示模式失败:', error);
      showStatus(error.message || '更新默认壁纸显示模式失败', 'error');
    }
  };

  const handleDefaultFileChange = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    setUploadingDefault(true);
    showStatus('正在上传默认壁纸...', 'info');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8081/api/personalization/wallpapers/default', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || '上传失败');
      }

      await onRefresh?.();
      showStatus('默认壁纸已更新，所有展板将使用新壁纸。', 'success');
    } catch (error) {
      console.error('上传默认壁纸失败:', error);
      showStatus(error.message || '上传默认壁纸失败', 'error');
    } finally {
      setUploadingDefault(false);
      event.target.value = '';
    }
  };

  const handleBoardFileChange = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file || !boardId) return;

    setUploadingBoard(true);
    showStatus('正在上传展板壁纸...', 'info');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/wallpapers`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || '上传失败');
      }

      const data = await onRefresh?.();
      const newlyUploaded = data?.boardWallpapers?.find((item) => item?.originalName === file.name);
      if (newlyUploaded?.id) {
        const appliedData = await handleSelectWallpaper(newlyUploaded.id, {
          showToast: false,
          displayMode: boardDisplayMode,
        });
        if (appliedData) {
          showStatus('展板壁纸上传并已应用。', 'success');
        }
      } else {
        showStatus('展板壁纸上传成功，请从列表中手动选择。', 'success');
      }
    } catch (error) {
      console.error('上传展板壁纸失败:', error);
      showStatus(error.message || '上传展板壁纸失败', 'error');
    } finally {
      setUploadingBoard(false);
      event.target.value = '';
    }
  };

  const handleSelectWallpaper = async (wallpaperId, options = {}) => {
    if (!boardId) return;
    const normalizedOptions = typeof options === 'object' && options !== null
      ? options
      : { showToast: options === undefined ? true : Boolean(options) };
    const { showToast = true, displayMode } = normalizedOptions;

    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/wallpapers/selection`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallpaperId, displayMode }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || '设置失败');
      }

      const latest = await onRefresh?.();
      if (showToast) {
        if (wallpaperId) {
          showStatus('已应用展板专属壁纸。', 'success');
        } else {
          showStatus('已恢复使用全局默认壁纸。', 'success');
        }
      }
      if (latest) {
        setBoardDisplayMode(latest.boardDisplayMode || latest.defaultDisplayMode || 'fit');
      }
      return latest;
    } catch (error) {
      console.error('设置展板壁纸失败:', error);
      showStatus(error.message || '设置展板壁纸失败', 'error');
      return null;
    }
  };

  if (!settings) {
    return (
      <div className="personalization-panel">
        <div className="personalization-scroll">
          <div className="win98-section">
            <div className="win98-section-title">加载中...</div>
            <div className="win98-section-body">正在加载个性化设置，请稍候。</div>
          </div>
        </div>
      </div>
    );
  }

  const { defaultWallpaper, boardWallpapers = [], selectedBoardWallpaperId } = settings;

  return (
    <div className="personalization-panel">
      <div className="personalization-summary">{appliedSummary}</div>

      <div className="personalization-scroll">
        {/* Theme Selection */}
        <section className="win98-section">
          <div className="win98-section-title">主题风格</div>
          <div className="win98-section-body">
            <label className="win98-radio">
              <input type="radio" checked readOnly />
              <span>Windows 98 （别的没做）</span>
            </label>
          </div>
        </section>

        {/* Default Wallpaper */}
        <section className="win98-section">
          <div className="win98-section-title">全局默认壁纸</div>
          <div className="win98-section-body">
            <div className="win98-field-description">
              将会应用到所有展板，除非某个展板单独指定了壁纸。
            </div>
            {displayModes.length > 0 && (
              <div className="win98-field-row">
                <span>显示模式：</span>
                <select
                  className="win98-select"
                  value={defaultDisplayMode}
                  onChange={handleDefaultDisplayModeChange}
                >
                  {displayModes.map((mode) => (
                    <option key={mode.id} value={mode.id}>
                      {mode.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="wallpaper-preview">
              {defaultWallpaper ? (
                <img src={`http://localhost:8081${defaultWallpaper.url}`} alt="默认壁纸预览" />
              ) : (
                <div className="wallpaper-empty">暂未设置默认壁纸</div>
              )}
            </div>
            {defaultWallpaper && (
              <div className="wallpaper-meta">
                <div>文件名：{defaultWallpaper.originalName || '未命名'}</div>
                <div>上传时间：{formatDate(defaultWallpaper.uploadedAt)}</div>
              </div>
            )}
            <div className="win98-button-row">
              <button
                className="win98-button"
                onClick={() => defaultFileInputRef.current?.click()}
                disabled={uploadingDefault}
              >
                {uploadingDefault ? '正在上传...' : '更换默认壁纸...'}
              </button>
            </div>
            <input
              ref={defaultFileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleDefaultFileChange}
            />
          </div>
        </section>

        {/* Board Wallpaper */}
        <section className="win98-section">
          <div className="win98-section-title">展板专属壁纸</div>
          <div className="win98-section-body">
            <div className="win98-field-description">
              当前展板：<strong>{boardName}</strong>
            </div>
            <div className="win98-field-description">
              上传多个壁纸后，可在下方快速切换。未选择时将使用全局默认壁纸。
            </div>

            {boardWallpapers.length === 0 ? (
              <div className="wallpaper-empty">暂未上传展板专属壁纸。</div>
            ) : (
              <div className="wallpaper-grid">
                {boardWallpapers.map((item) => {
                  const isSelected = item.id === selectedBoardWallpaperId;
                  return (
                    <div
                      key={item.id}
                      className={`wallpaper-card ${isSelected ? 'selected' : ''}`}
                    >
                      <div className="wallpaper-card-preview">
                        <img src={`http://localhost:8081${item.url}`} alt={item.originalName || '壁纸'} />
                      </div>
                      <div className="wallpaper-card-info">
                        <div className="wallpaper-card-name">{item.originalName || '未命名壁纸'}</div>
                        <div className="wallpaper-card-time">{formatDate(item.uploadedAt)}</div>
                      </div>
                      <div className="win98-button-row">
                        <button
                          className="win98-button"
                          onClick={() => handleSelectWallpaper(item.id, { displayMode: boardDisplayMode })}
                          disabled={isSelected}
                        >
                          {isSelected ? '正在使用' : '设为当前壁纸'}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {displayModes.length > 0 && (
              <div className="win98-field-row">
                <span>显示模式：</span>
                <select
                  className="win98-select"
                  value={boardDisplayMode}
                  onChange={handleBoardDisplayModeChange}
                >
                  {displayModes.map((mode) => (
                    <option key={mode.id} value={mode.id}>
                      {mode.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="win98-button-row">
              <button
                className="win98-button"
                onClick={() => boardFileInputRef.current?.click()}
                disabled={uploadingBoard}
              >
                {uploadingBoard ? '正在上传...' : '上传展板壁纸...'}
              </button>
              <button
                className="win98-button"
                onClick={() => handleSelectWallpaper(null, { displayMode: boardDisplayMode })}
                disabled={!selectedBoardWallpaperId}
              >
                恢复默认壁纸
              </button>
            </div>
            <input
              ref={boardFileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleBoardFileChange}
            />
          </div>
        </section>

        {/* Language */}
        <section className="win98-section">
          <div className="win98-section-title">语言</div>
          <div className="win98-section-body">
            <div className="win98-field-description">目前仅支持简体中文。</div>
            <select className="win98-select" value="zh-CN" disabled>
              <option value="zh-CN">简体中文</option>
            </select>
          </div>
        </section>
      </div>

      {statusMessage && (
        <div className={`personalization-status personalization-status-${statusType}`}>
          {statusMessage}
        </div>
      )}
    </div>
  );
};

export default PersonalizationPanel;

