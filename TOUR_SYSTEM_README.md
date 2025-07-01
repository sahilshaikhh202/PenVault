# PenVault Onboarding Tour System

## Overview

The PenVault Onboarding Tour System is a progressive, contextual tour designed to help new users understand and navigate the platform. It provides step-by-step guidance through key features without overwhelming users with information.

## Features

### ✅ Core Features
- **Progressive Tour**: Shows one tip at a time, not overwhelming users
- **Contextual Triggers**: Tips appear only when users visit specific pages
- **Tour State Tracking**: Progress saved in localStorage and database
- **Resume Later**: Users can restart the tour anytime via "?" button
- **User-Type Conditional**: Different tours for different user types
- **Non-Intrusive**: Easy to disable and doesn't break existing functionality

### 🎯 Tour Steps

#### Welcome & Navigation (Home Page)
1. **Welcome Modal**: Introduces PenVault and the tour
2. **Navigation Bar**: Explains the main navigation
3. **Write Button**: Shows how to start creating content
4. **Profile Menu**: Explains profile and settings access

#### Page-Specific Tours
- **Discover Page**: Explains content discovery
- **Feed Page**: Shows how to follow users and see updates
- **Statistics Page**: Explains Pulse Score and analytics
- **Redeem Points Page**: Shows point redemption system
- **Settings Page**: Explains account management

## Technical Implementation

### Database Schema

```python
class User(UserMixin, db.Model):
    # ... existing fields ...
    
    # Tour tracking
    tour_completed = db.Column(db.Boolean, default=False)
    tour_progress = db.Column(db.JSON, default=dict)  # Store tour step progress
```

### Files Structure

```
app/
├── static/
│   ├── css/
│   │   └── tour.css          # Tour styling
│   └── js/
│       └── tour.js           # Tour functionality
├── templates/
│   ├── base.html             # Includes tour CSS/JS
│   └── test_tour.html        # Test page
└── routes.py                 # Tour API endpoints
```

### Key Components

#### 1. Tour JavaScript (`tour.js`)
- **PenVaultTour Class**: Main tour controller
- **Step Management**: Handles tour progression
- **Tooltip Creation**: Dynamic tooltip positioning
- **Progress Tracking**: Saves to localStorage and server
- **Responsive Design**: Adapts to different screen sizes

#### 2. Tour CSS (`tour.css`)
- **Modern Design**: Clean, accessible tooltips
- **Dark Mode Support**: Adapts to user theme
- **Responsive**: Works on mobile and desktop
- **Accessibility**: High contrast and reduced motion support

#### 3. API Endpoints
- `POST /api/tour/progress`: Updates tour progress
- `GET /test-tour`: Test page for development

## Usage

### For New Users
1. **Automatic Trigger**: Tour starts automatically after first login
2. **Progressive Steps**: One step at a time with clear navigation
3. **Skip Option**: Users can skip at any time
4. **Completion**: Shows welcome message when finished

### For Existing Users
1. **Manual Restart**: Click "?" button in navigation
2. **Progress Reset**: Starts from beginning
3. **Persistent**: Progress saved across sessions

### For Developers
1. **Test Page**: Visit `/test-tour` to test functionality
2. **Customization**: Modify `tour.js` for new steps
3. **Styling**: Update `tour.css` for visual changes

## Configuration

### Adding New Tour Steps

1. **Define Step in `tour.js`**:
```javascript
{
    id: 'new_step',
    title: 'Step Title',
    content: 'Step description',
    target: '.css-selector',  // Element to highlight
    position: 'bottom',       // Tooltip position
    showOn: ['/page-path']    // Pages to show on
}
```

2. **Add to Page-Specific Steps**:
```javascript
const pageSpecificSteps = {
    '/new-page': [
        // Add your new step here
    ]
};
```

### Customizing Styling

1. **Tooltip Appearance**: Modify `.penvault-tour-tooltip` in `tour.css`
2. **Highlight Effects**: Update `.penvault-tour-highlight` styles
3. **Dark Mode**: Add `[data-theme="dark"]` selectors

## Migration

### For Existing Users
Run the migration script to add tour fields:

```bash
python add_tour_fields_migration.py
```

This will:
- Add `tour_completed` field (default: `False`)
- Add `tour_progress` field (default: `{}`)
- Preserve existing user data

## Testing

### Manual Testing
1. **New User Flow**:
   - Register new account
   - Login and verify tour starts
   - Complete tour steps
   - Verify completion message

2. **Existing User Flow**:
   - Login with existing account
   - Click "?" button to restart tour
   - Verify tour progression
   - Check progress persistence

3. **Responsive Testing**:
   - Test on mobile devices
   - Verify tooltip positioning
   - Check accessibility features

### Automated Testing
- Tour initialization
- Step progression
- Progress saving
- API endpoints
- Responsive behavior

## Accessibility

### Features
- **Screen Reader Support**: Proper ARIA labels
- **Keyboard Navigation**: Full keyboard support
- **High Contrast**: Enhanced visibility
- **Reduced Motion**: Respects user preferences
- **Focus Management**: Clear focus indicators

### Compliance
- WCAG 2.1 AA compliant
- Supports assistive technologies
- Responsive to user preferences

## Performance

### Optimizations
- **Lazy Loading**: Tour loads only when needed
- **Minimal DOM**: Efficient tooltip creation
- **Debounced Resize**: Smooth window resizing
- **Local Storage**: Fast progress saving

### Monitoring
- Tour completion rates
- Step progression analytics
- User engagement metrics
- Performance impact

## Troubleshooting

### Common Issues

1. **Tour Not Starting**:
   - Check user authentication
   - Verify tour progress not completed
   - Check browser console for errors

2. **Tooltip Positioning**:
   - Verify target element exists
   - Check CSS conflicts
   - Test responsive behavior

3. **Progress Not Saving**:
   - Check API endpoint
   - Verify database connection
   - Check localStorage permissions

### Debug Mode
Enable debug logging in `tour.js`:
```javascript
// Add to PenVaultTour constructor
this.debug = true;
```

## Future Enhancements

### Planned Features
- **A/B Testing**: Different tour variants
- **Analytics Integration**: Detailed user behavior
- **Custom Tours**: User-defined tour paths
- **Multilingual Support**: Internationalization
- **Video Tours**: Embedded video content

### Extensibility
- **Plugin System**: Third-party tour extensions
- **API Integration**: External tour management
- **Custom Themes**: Branded tour appearances
- **Advanced Triggers**: Complex tour conditions

## Support

### Documentation
- This README
- Code comments
- API documentation
- User guides

### Contact
- Development team
- User support
- Bug reports
- Feature requests

---

**Note**: This tour system is designed to be lightweight, accessible, and easily maintainable. It integrates seamlessly with the existing PenVault platform without disrupting current functionality. 