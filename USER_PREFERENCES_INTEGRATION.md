# User Preferences Integration

This document describes the integration of external user preferences APIs into the Porta BFF system, enabling personalized user experiences based on investment preferences, communication styles, and interaction history.

## Overview

The Porta BFF system now integrates with external user preferences services to provide:

1. **Personalized Communication**: Adapt responses based on user's preferred communication style (simple, technical, detailed)
2. **Investment Context**: Consider user's risk tolerance, experience level, and investment goals
3. **Sector Preferences**: Provide recommendations aligned with user's preferred investment sectors
4. **Interaction Tracking**: Monitor user engagement and satisfaction for continuous improvement
5. **Preference History**: Maintain audit trail of preference changes over time

## Architecture

```
Porta BFF → External User Preferences API
     ↓
  User Preferences Service
     ↓
  PostgreSQL Database
```

## API Endpoints

### Base URLs
- **User Preferences**: `http://localhost:8000/api/v1/user-preferences/`
- **User Interactions**: `http://localhost:8000/api/v1/user-interactions/`
- **Preference History**: `http://localhost:8000/api/v1/preference-history/`

### Available Tools

#### 1. User Preferences Management
- `get_user_preferences(user_id)`: Retrieve user's complete preference profile
- `create_user_preferences(...)`: Create new user preferences
- `update_user_preferences(...)`: Update existing preferences

#### 2. User Interaction Tracking
- `record_user_interaction(...)`: Log user interactions and satisfaction
- `get_user_interactions(...)`: Retrieve interaction history
- `get_preference_history(...)`: View preference change history

## User Preference Fields

### Core Investment Profile
- **experience_level**: `["beginner", "intermediate", "advanced", "expert"]`
- **investment_style**: `["conservative", "moderate", "aggressive", "day_trader", "swing_trader", "long_term"]`
- **risk_tolerance**: `["low", "medium", "high"]`
- **preferred_timeframe**: `["short_term", "medium_term", "long_term"]`

### Communication Preferences
- **communication_style**: `["simple", "technical", "detailed"]`
- **language**: Language code (e.g., "en", "es", "fr")
- **currency**: Currency code (e.g., "USD", "EUR", "GBP")
- **timezone**: User's timezone

### Investment Preferences
- **preferred_sectors**: Array of preferred sectors (e.g., ["technology", "healthcare", "energy"])
- **investment_goals**: Array of investment objectives (e.g., ["growth", "retirement", "income"])
- **preferred_asset_classes**: Array of preferred asset types (e.g., ["stocks", "etfs", "bonds"])

## Usage Examples

### Getting User Preferences
```python
# Retrieve user preferences to personalize responses
preferences = get_user_preferences("user-123")
if preferences["ok"]:
    user_profile = preferences["preferences"]
    # Adapt communication based on user's style
    if user_profile["communication_style"] == "simple":
        # Use simple language
        response = "Your portfolio looks good!"
    elif user_profile["communication_style"] == "technical":
        # Use technical analysis
        response = "Your portfolio shows a Sharpe ratio of 1.2 with 15% volatility..."
```

### Recording User Interactions
```python
# Track when users use portfolio tools
record_user_interaction(
    user_id="user-123",
    interaction_type="tool_used",
    content={
        "tool_name": "portfolio_analyzer",
        "analysis_type": "risk_assessment"
    },
    satisfaction_score=5
)
```

### Updating User Preferences
```python
# Update user's risk tolerance
update_user_preferences(
    user_id="user-123",
    risk_tolerance="high",
    preferred_sectors=["technology", "healthcare", "energy"]
)
```

## Integration with Existing Tools

### Portfolio Tools
- **Before executing**: Check user's risk tolerance and preferred asset classes
- **After execution**: Record interaction and satisfaction
- **Recommendations**: Consider user's preferred sectors and investment goals

### Watchlist Tools
- **Suggestions**: Align with user's preferred sectors and asset classes
- **Communication**: Adapt to user's preferred communication style
- **Tracking**: Record all watchlist-related interactions

### Web Search Tools
- **Results**: Prioritize content relevant to user's investment preferences
- **Language**: Use user's preferred language when available
- **Tracking**: Monitor search patterns and satisfaction

## System Prompt Updates

The agent's system prompt has been updated to include:

1. **User Preferences Awareness**: Instructions to check user preferences before providing recommendations
2. **Communication Adaptation**: Guidelines for adapting responses based on user's communication style
3. **Investment Context**: Rules for considering user's risk tolerance and investment goals
4. **Interaction Tracking**: Requirements to record user interactions for continuous improvement

## Configuration

### Environment Variables
```bash
# User Preferences API URLs (configurable)
USER_PREFERENCES_API_URL=http://localhost:8000/api/v1/user-preferences/
USER_INTERACTIONS_API_URL=http://localhost:8000/api/v1/user-interactions/
PREFERENCE_HISTORY_API_URL=http://localhost:8000/api/v1/preference-history/
```

### Default Values
- **Base URL**: `http://localhost:8000/api/v1/`
- **Timeout**: 10 seconds for all API calls
- **Retry Logic**: Basic error handling with connection and timeout detection

## Testing

Run the test script to verify API integration:

```bash
python test_user_preferences.py
```

This will test:
1. Creating user preferences
2. Retrieving user preferences
3. Updating user preferences
4. Recording user interactions
5. Retrieving interaction history
6. Accessing preference history

## Error Handling

### Connection Issues
- Graceful fallback when external services are unavailable
- User-friendly error messages without exposing technical details
- Automatic retry logic for transient failures

### Validation Errors
- Input validation before API calls
- Clear error messages for invalid data
- Proper HTTP status code handling

### Timeout Handling
- Configurable timeout values (default: 10 seconds)
- Timeout-specific error messages
- Graceful degradation when services are slow

## Benefits

### For Users
1. **Personalized Experience**: Responses tailored to their investment knowledge and preferences
2. **Consistent Communication**: Language and detail level that matches their comfort zone
3. **Relevant Recommendations**: Suggestions aligned with their investment goals and risk tolerance
4. **Progress Tracking**: Visibility into their interaction history and preference evolution

### For System
1. **Better Engagement**: Higher user satisfaction through personalized interactions
2. **Data Insights**: Rich interaction data for system improvement
3. **User Retention**: Personalized experiences increase user stickiness
4. **Continuous Learning**: Track how preferences change over time

## Future Enhancements

### Planned Features
1. **Machine Learning Integration**: Use interaction data to predict user needs
2. **A/B Testing**: Test different communication styles and track effectiveness
3. **Preference Recommendations**: Suggest preference updates based on usage patterns
4. **Multi-language Support**: Full internationalization based on user preferences

### Integration Opportunities
1. **Portfolio Analytics**: Use preferences to enhance portfolio analysis tools
2. **Market Alerts**: Send personalized market updates based on sector preferences
3. **Educational Content**: Recommend learning materials based on experience level
4. **Social Features**: Connect users with similar investment profiles

## Troubleshooting

### Common Issues
1. **API Connection Failures**: Check if external services are running
2. **Timeout Errors**: Verify network connectivity and service performance
3. **Validation Errors**: Ensure all required fields are provided
4. **Permission Issues**: Verify API access and authentication

### Debug Mode
Enable detailed logging by setting log level to DEBUG in the configuration.

## Support

For issues with the user preferences integration:
1. Check the test script output for specific error details
2. Verify external API service status
3. Review network connectivity and firewall settings
4. Check API endpoint URLs and authentication

---

*This integration enables Porta to provide truly personalized financial assistance while maintaining the security and reliability of the existing system.*
