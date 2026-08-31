const fs = require('fs');
const content = fs.readFileSync('C:/Users/Person/Desktop/GALL/src/pages/host/HostSettingsPage.tsx', 'utf8');

const startIdx = content.indexOf('const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {');
const endIdx = content.indexOf('  };', content.indexOf('  };', content.indexOf('const renderMediaGrid'))) + 3;

const before = content.substring(0, content.indexOf('const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {'));
const after = content.substring(content.indexOf('  };', content.indexOf('  };', content.indexOf('const renderMediaGrid'))) + 3;

const newFunc = `const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {
    const items = getMediaForCategory(category);
    const key = getCategoryKey(category);
    const uploadState = uploadStates[key] || { isUploading: false };

    return (
      <div className="host-settings__media-category">
        <div className="host-settings__media-category-header">
          <h3 className="host-settings__media-category-title">{category.label}</h3>
          <p className="host-settings__media-category-desc">{category.description}</p>
        </div>
        <div className="host-settings__media-grid">
          {items.length === 0 ? (
            <div className="host-settings__media-empty">
              <p>No images assigned yet.</p>
            </div>
          ) : (
            <div className="host-settings__media-thumbnails">
              {items.map((m) => (
                <div key={m.id} className="host-settings__media-thumb">
                  <div className="host-settings__media-thumb-inner">
                    {m.type === 'video' ? (
                      <video src={m.src} muted playsInline />
                    ) : (
                      <img src={m.src} alt={m.caption || m.guestName} loading="lazy" />
                    )}
                    <div className="host-settings__media-overlay">
                      <button
                        type="button"
                        className="host-settings__media-action is-reassign"
                        onClick={(e) => {
                          e.stopPropagation();
                          const newRole = window.prompt('New role (HERO, SLIDESHOW, HOST_SLIDESHOW):');
                          const newPage = window.prompt('New page (LANDING, GUEST, CAMERA, HOST):');
                          if (newRole) handleReassign(m.mediaId || m.id, newRole as MediaRole, newPage as MediaPage);
                        }}
                        title="Reassign"
                      >
                        ⟳
                      </button>
                      <button
                        type="button"
                        className="host-settings__media-action is-delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(m.mediaId || m.id);
                        }}
                        title="Remove"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="host-settings__media-upload">
          <label className="host-settings__upload-label">
            <input
              type="file"
              accept="image/*,video/*"
              multiple
              onChange={(e) => {
                const files = Array.from(e.target.files);
                files.forEach(file => handleUpload(categoryKey, file, category.role, category.page));
              }}
              className="host-settings__file-input"
            />
            <span className="host-settings__upload-text">
              {uploadState.isUploading ? 'Uploading...' : 'Click or drag to upload images'}
            </span>
            {uploadState.error && <span className="host-settings__upload-error">{uploadState.error}</span>}
          </label>
        </div>
      </div>
    );
  };`;

const content = fs.readFileSync('C:/Users/Person/Desktop/GALL/src/pages/host/HostSettingsPage.tsx', 'utf8');
const startIdx = content.indexOf('const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {');
const endIdx = content.indexOf('  };', content.indexOf('  };', content.indexOf('const renderMediaGrid'))) + 3;
const before = content.substring(0, content.indexOf('const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {'));
const after = content.substring(content.indexOf('  };', content.indexOf('  };', content.indexOf('const renderMediaGrid'))) + 3;
const newFunc = require('fs').readFileSync('C:/Users/Person/Desktop/GALL/newRenderMediaGrid.txt', 'utf8');
const newContent = content.substring(0, content.indexOf('const renderMediaGrid = (category: { role: MediaRole; page?: MediaPage }) => {')) + newFunc + content.substring(content.indexOf('  };', content.indexOf('  };', content.indexOf('const renderMediaGrid'))) + 3);
fs.writeFileSync('C:/Users/Person/Desktop/GALL/src/pages/host/HostSettingsPage.tsx', before + newFunc + after, 'utf8');
console.log('Done');