import React, { useEffect, useMemo, useRef, useState } from 'react';
import './PersonalizationPanel.css';
import { useLanguage } from '../i18n/LanguageContext';

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
  const { t, language, updateLanguage } = useLanguage();
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
      return t('current_using_solid');
    }
    const { type, originalName } = settings.appliedWallpaper;
    if (type === 'board') {
      return `${t('current_using_board')} (${originalName || t('unnamed')})`;
    }
    if (type === 'default') {
      return `${t('current_using_default')} (${settings.appliedWallpaper.originalName || t('unnamed')})`;
    }
    return t('current_using_solid');
  }, [settings, t]);

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
      showStatus(t('wallpaper_mode_updated'), 'success');
    }
  };

  const handleDefaultDisplayModeChange = async (event) => {
    const mode = event.target.value;
    setDefaultDisplayMode(mode);
    showStatus(t('updating_display_mode'), 'info');
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
      showStatus(t('default_display_mode_updated'), 'success');
    } catch (error) {
      console.error('更新默认壁纸显示模式失败:', error);
      showStatus(error.message || t('default_display_mode_updated'), 'error');
    }
  };

  const handleDefaultFileChange = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    setUploadingDefault(true);
    showStatus(t('uploading_default_wallpaper'), 'info');
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
      showStatus(t('default_wallpaper_updated'), 'success');
    } catch (error) {
      console.error('上传默认壁纸失败:', error);
      showStatus(error.message || t('default_wallpaper_updated'), 'error');
    } finally {
      setUploadingDefault(false);
      event.target.value = '';
    }
  };

  const handleBoardFileChange = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file || !boardId) return;

    setUploadingBoard(true);
    showStatus(t('uploading_board_wallpaper'), 'info');
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
          showStatus(t('board_wallpaper_applied'), 'success');
        }
      } else {
        showStatus(t('board_wallpaper_uploaded'), 'success');
      }
    } catch (error) {
      console.error('上传展板壁纸失败:', error);
      showStatus(error.message || t('board_wallpaper_uploaded'), 'error');
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
          showStatus(t('board_wallpaper_applied_msg'), 'success');
        } else {
          showStatus(t('restored_default_wallpaper'), 'success');
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
              <div className="win98-section-title">{t('loading')}</div>
              <div className="win98-section-body">{t('loading_personalization')}</div>
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
            <div className="win98-section-title">{t('theme_style')}</div>
            <div className="win98-section-body">
              <label className="win98-radio">
                <input type="radio" checked readOnly />
                <span>{t('theme_win98')}</span>
              </label>
            </div>
          </section>

          {/* Default Wallpaper */}
          <section className="win98-section">
            <div className="win98-section-title">{t('default_wallpaper')}</div>
            <div className="win98-section-body">
              <div className="win98-field-description">
                {t('default_wallpaper_desc')}
              </div>
              {displayModes.length > 0 && (
                <div className="win98-field-row">
                  <span>{t('display_mode')}</span>
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
                  <img src={`http://localhost:8081${defaultWallpaper.url}`} alt={t('wallpaper_preview')} />
                ) : (
                  <div className="wallpaper-empty">{t('no_default_wallpaper')}</div>
                )}
              </div>
              {defaultWallpaper && (
                <div className="wallpaper-meta">
                  <div>{t('filename')}{defaultWallpaper.originalName || t('unnamed')}</div>
                  <div>{t('upload_time')}{formatDate(defaultWallpaper.uploadedAt)}</div>
                </div>
              )}
              <div className="win98-button-row">
                <button
                  className="win98-button"
                  onClick={() => defaultFileInputRef.current?.click()}
                  disabled={uploadingDefault}
                >
                  {uploadingDefault ? t('uploading') : t('change_default_wallpaper')}
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
            <div className="win98-section-title">{t('board_wallpaper')}</div>
            <div className="win98-section-body">
              <div className="win98-field-description">
                {t('current_board')}<strong>{boardName}</strong>
              </div>
              <div className="win98-field-description">
                {t('board_wallpaper_desc')}
              </div>

              {boardWallpapers.length === 0 ? (
                <div className="wallpaper-empty">{t('no_board_wallpaper')}</div>
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
                          <img src={`http://localhost:8081${item.url}`} alt={item.originalName || t('wallpaper')} />
                        </div>
                        <div className="wallpaper-card-info">
                          <div className="wallpaper-card-name">{item.originalName || t('unnamed_wallpaper')}</div>
                          <div className="wallpaper-card-time">{formatDate(item.uploadedAt)}</div>
                        </div>
                        <div className="win98-button-row">
                          <button
                            className="win98-button"
                            onClick={() => handleSelectWallpaper(item.id, { displayMode: boardDisplayMode })}
                            disabled={isSelected}
                          >
                            {isSelected ? t('in_use') : t('set_as_current')}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {displayModes.length > 0 && (
                <div className="win98-field-row">
                  <span>{t('display_mode')}</span>
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
                  {uploadingBoard ? t('uploading') : t('upload_board_wallpaper')}
                </button>
                <button
                  className="win98-button"
                  onClick={() => handleSelectWallpaper(null, { displayMode: boardDisplayMode })}
                  disabled={!selectedBoardWallpaperId}
                >
                  {t('restore_default_wallpaper')}
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
          <div className="win98-section-title">{t('language')}</div>
          <div className="win98-section-body">
            <div className="win98-field-description">{t('select_language')}</div>
            <select 
              className="win98-select" 
              value={language} 
              onChange={(e) => updateLanguage(e.target.value)}
            >
              {settings.availableLanguages?.map(lang => (
                <option key={lang.code} value={lang.code}>{lang.label}</option>
              ))}
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

