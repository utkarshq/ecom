# Changelog

## [Unreleased]

### Added
- Artist application process with two-step verification
- Artist dashboard for managing artworks and viewing sales/commission information
- Tier system for artists based on sales performance
- Commission calculation system considering multiple factors (tier, product type, referrals)
- Referral system for artists to generate unique links for their artworks
- Admin interface for managing artists, tiers, and commission rates
- Celery task for periodic recalculation of artist tiers

### Changed
- Extended Saleor's Order model to include referral information
- Updated admin views to include new artist management features

### Fixed
- Improved performance of commission calculations with database indexing

## [0.1.0] - YYYY-MM-DD

### Added
- Initial project setup
- Integration with Saleor e-commerce platform

## Details of Major Features

### Artist Application Process
- Two-step verification: basic information and legal document upload
- Admin review and approval/rejection functionality
- Email notifications for application status changes

### Artist Dashboard
- Display of sales, commissions, and tier status
- Management of permitted artworks
- Generation of referral links for artworks

### Tier System
- Configurable tiers based on sales thresholds or percentiles
- Automatic recalculation of tiers using Celery tasks

### Commission Calculation
- Factors considered: artist's tier, product type, and referral status
- Highest applicable rate is used for each sale

### Referral System
- Unique referral link generation for each artwork
- Tracking of purchases made through referral links
- Higher commission rates for referral sales

### Admin Interface
- Management of artist applications, tiers, and commission rates
- Association of artworks with artists
- Recalculation of sales and commissions

## Code References

### Artist Admin Interface
- `artist/admin.py`: Custom admin actions for artists
- `artist/saleor_api.py`: Functions for artist-related data retrieval and calculations

### Artist Models
- `artist/models.py`: Models for Artist, TierSettings, CommissionRate, ReferralLink, and HistoricalCommissionRate

### Artist Views
- `artist/views.py`: Views for artist dashboard and artwork management

### Artist Forms
- `artist/forms.py`: Forms for artist application and artwork creation

### Artist URLs
- `artist/urls.py`: URL configuration for artist-related views

### Artist Templates
- `artist/templates/artist/`: Templates for artist dashboard and artwork management

### Artist Static Files
- `artist/static/artist/`: Static files for artist dashboard and artwork management

### Artist Translations
- `artist/locale/`: Translation files for artist dashboard and artwork management

### Artist Tests
- `artist/tests/`: Test cases for artist-related functionality

### Artist Utilities
- `artist/utils.py`: Utility functions for artist-related operations

### Artist Signals
- `artist/signals.py`: Signal handlers for artist-related operations

### Artist Notifications
- `artist/notifications.py`: Functions for sending notifications to artists

### Artist Tasks
- `artist/tasks.py`: Celery tasks for artist-related operations

### Artist Views
- `artist/views.py`: Views for artist dashboard and artwork management


## Setup Instructions

1. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run database migrations:
   ```
   python manage.py migrate
   ```

3. Set up Celery for periodic tasks:
   - Ensure Redis is installed and running
   - Start Celery worker: `celery -A project worker -l info`
   - Start Celery beat: `celery -A project beat -l info`

4. Configure email settings in `settings.py` for notification system

5. Run the development server:
   ```
   python manage.py runserver
   ```

## Next Steps
- Implement more detailed analytics for artists
- Enhance the user interface for the artist dashboard
- Develop a more extensive permission system for different staff roles
- Integrate with additional payment gateways

