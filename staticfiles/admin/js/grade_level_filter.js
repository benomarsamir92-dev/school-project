// grade_level_filter.js - Level filter for Grade admin
document.addEventListener('DOMContentLoaded', function() {
    // Only run on grade add page
    if (window.location.pathname.includes('/grade/add/') || 
        (window.location.pathname.includes('/school_management/grade/add/'))) {
        
        addLevelFilter();
    }
});

function addLevelFilter() {
    // Get the student field container
    const studentField = document.querySelector('.field-student');
    if (!studentField) return;
    
    // Create level filter HTML
    const levelFilterHtml = `
        <div class="form-row" style="background: #f8f8f8; padding: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
            <div>
                <label style="font-weight: bold; color: #333;" for="level_filter">
                    📚 Filter Students by Level:
                </label>
                <select name="level_filter" id="level_filter" style="margin-left: 10px; padding: 5px;">
                    <option value="">--- All Levels ---</option>
                </select>
                <button type="button" id="apply_filter" style="margin-left: 10px; padding: 5px 10px; background: #417690; color: white; border: none; border-radius: 3px;">
                    Apply Filter
                </button>
                <p class="help" style="margin-top: 5px; color: #666;">
                    Select a level to filter the student list. This will only show students from the selected level.
                </p>
            </div>
        </div>
    `;
    
    // Insert the filter before the student field
    studentField.insertAdjacentHTML('beforebegin', levelFilterHtml);
    
    // Load available levels
    loadAvailableLevels();
    
    // Add event listeners
    document.getElementById('apply_filter').addEventListener('click', applyLevelFilter);
    document.getElementById('level_filter').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyLevelFilter();
        }
    });
}

function loadAvailableLevels() {
    // Get current level from URL
    const urlParams = new URLSearchParams(window.location.search);
    const currentLevel = urlParams.get('level');
    
    // This would typically come from your Django context, but we'll use a fallback
    // For now, we'll extract levels from the existing student dropdown
    const studentSelect = document.getElementById('id_student');
    if (studentSelect) {
        const levels = new Set();
        
        // Extract levels from option text (assuming format: "Name - Level" or similar)
        Array.from(studentSelect.options).forEach(option => {
            if (option.text && option.value) {
                // Try to extract level from the text
                const match = option.text.match(/\((.*?)\)|-\s*(.*?)$/);
                if (match) {
                    const level = match[1] || match[2];
                    if (level && level.trim()) {
                        levels.add(level.trim());
                    }
                }
            }
        });
        
        // Add levels to the filter dropdown
        const levelFilter = document.getElementById('level_filter');
        levels.forEach(level => {
            const option = document.createElement('option');
            option.value = level;
            option.textContent = level;
            if (level === currentLevel) {
                option.selected = true;
            }
            levelFilter.appendChild(option);
        });
        
        // If we have a current level, show a note
        if (currentLevel) {
            showCurrentLevelNote(currentLevel);
        }
    }
}

function applyLevelFilter() {
    const levelFilter = document.getElementById('level_filter');
    const selectedLevel = levelFilter.value;
    
    const url = new URL(window.location);
    
    if (selectedLevel) {
        url.searchParams.set('level', selectedLevel);
    } else {
        url.searchParams.delete('level');
    }
    
    // Reload the page with the filter
    window.location.href = url.toString();
}

function showCurrentLevelNote(level) {
    const filterContainer = document.querySelector('.field-student').previousElementSibling;
    const helpText = filterContainer.querySelector('.help');
    
    if (helpText) {
        helpText.innerHTML = `
            <strong>Currently filtering by:</strong> <span style="color: green;">${level}</span><br>
            Students from other levels are hidden. Change the filter to see different levels.
        `;
    }
    
    // Also update the student field label
    const studentLabel = document.querySelector('label[for="id_student"]');
    if (studentLabel) {
        const originalText = studentLabel.textContent.replace(/ \(\*\)$/, '');
        studentLabel.textContent = `${originalText} (*)`;
        studentLabel.title = `Filtered by level: ${level}`;
    }
}

// Alternative: Auto-apply filter when selection changes (uncomment if preferred)
/*
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const levelFilter = document.getElementById('level_filter');
        if (levelFilter) {
            levelFilter.addEventListener('change', function() {
                applyLevelFilter();
            });
        }
    }, 1000);
});
*/