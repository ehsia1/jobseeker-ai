# Supported Professions & Job Boards

The JobSeeker AI system now supports multiple professions and automatically selects the most relevant job boards for each field.

## Supported Professions

### Technology
- **Software Engineer**: GitHub Jobs, HackerNews, RemoteOK, AngelList, Indeed, LinkedIn
- **Data Scientist**: RemoteOK, HackerNews, AngelList, Indeed, LinkedIn
- **DevOps Engineer**: RemoteOK, HackerNews, GitHub, Indeed, LinkedIn
- **Product Manager**: AngelList, RemoteOK, Indeed, LinkedIn, FlexJobs

### Creative & Design
- **Designer** (UX/UI/Graphic): AngelList, RemoteOK, FlexJobs, Upwork, Indeed, LinkedIn
- **Writer** (Content/Technical): FlexJobs, Upwork, RemoteOK, Indeed, LinkedIn
- **Content Creator**: FlexJobs, Upwork, RemoteOK, Indeed

### Business & Sales
- **Sales Professional**: AngelList, RemoteOK, Indeed, LinkedIn, FlexJobs
- **Marketing Specialist**: AngelList, RemoteOK, FlexJobs, Indeed, LinkedIn
- **Business Analyst**: Indeed, LinkedIn, AngelList, FlexJobs

### Operations & Management
- **Operations Manager**: AngelList, Indeed, LinkedIn, FlexJobs
- **Project Manager**: Indeed, LinkedIn, AngelList, FlexJobs, RemoteOK
- **Administrative**: FlexJobs, Indeed, LinkedIn, Upwork

### Finance & Accounting
- **Accountant**: Indeed, LinkedIn, FlexJobs, Upwork
- **Finance Professional**: Indeed, LinkedIn, AngelList

### Healthcare
- **Healthcare Professional**: Indeed, LinkedIn, FlexJobs
- **Nurse**: Indeed, LinkedIn, FlexJobs

### Education
- **Teacher**: Indeed, LinkedIn, FlexJobs
- **Trainer/Instructor**: FlexJobs, Indeed, LinkedIn, Upwork

### Customer Service
- **Customer Service Rep**: FlexJobs, RemoteOK, Indeed, LinkedIn
- **Support Specialist**: RemoteOK, FlexJobs, Indeed, LinkedIn

### Legal
- **Legal Professional**: Indeed, LinkedIn, FlexJobs, Upwork
- **Paralegal**: Indeed, LinkedIn, FlexJobs

### Freelance & Consulting
- **Freelancer** (Any field): Upwork, FlexJobs, RemoteOK
- **Consultant**: Upwork, Indeed, LinkedIn, FlexJobs

## Job Board Coverage

### Active Integrations
1. **RemoteOK** ✅ - Remote jobs across all fields
2. **HackerNews** ✅ - Tech-focused "Who's Hiring" threads
3. **GitHub Jobs** ✅ - Open source and tech positions
4. **AngelList/Wellfound** 🔧 - Startup jobs (API ready)
5. **FlexJobs** 🔧 - Flexible and remote work (API ready)
6. **Upwork** 🔧 - Freelance opportunities (API ready)
7. **Indeed** 🔧 - General job board (API ready)
8. **LinkedIn** 🔧 - Professional network (OAuth required)

✅ = Fully integrated and working
🔧 = Structure ready, needs API credentials

## How It Works

1. **Automatic Selection**: Based on user's profession, the system automatically selects the most relevant job boards
2. **Keyword Intelligence**: If no profession is specified, the system analyzes keywords to suggest the best profession category
3. **Multi-Source Search**: Searches multiple job boards concurrently for faster results
4. **Deduplication**: Removes duplicate listings across different job boards
5. **Skill Matching**: Matches jobs based on user's skills and preferences

## Usage Examples

### API Request
```json
{
  "profession": "marketing",
  "keywords": ["digital", "growth", "seo"],
  "remote_only": true,
  "limit": 10
}
```

### Response
The system will automatically search:
- AngelList (for startup marketing roles)
- RemoteOK (for remote marketing positions)
- FlexJobs (for flexible marketing work)
- Indeed (for general marketing jobs)
- LinkedIn (for professional marketing opportunities)

## Adding New Professions

To add support for a new profession, update the `PROFESSION_SEARCHERS` dictionary in `/backend/searchers/searcher_registry.py`:

```python
"new_profession": [
    SearcherClass1,
    SearcherClass2,
    # ... relevant searchers
]
```

## Future Enhancements

1. **More Job Boards**: Dice (tech), Monster, CareerBuilder, ZipRecruiter
2. **Industry-Specific**: 
   - Healthcare: HealthcareJobSite, Nurse.com
   - Education: HigherEdJobs, TeachingJobs
   - Finance: eFinancialCareers, WallStreetOasis
3. **Location-Based**: Local job boards based on user location
4. **Niche Boards**: 
   - Remote.co, We Work Remotely (remote work)
   - Dribbble, Behance (design)
   - ProBlogger (writing)
   - SalesJobs.com (sales)