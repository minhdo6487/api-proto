# Notify

## Get campaigns

```
GET dev.golfconnect24.com/api/v2/notify/campaigns/
```

### Permission

- Admin account

### Params

- `page` < int: paginate when need (default `1`)

### Response

- 200 if success
- 401 if unauthorized

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "hello",
            "body": "hello",
            "gender": "-",
            "age_min": 18,
            "age_max": 70,
            "city_ids": "",
            "sent_at": null,
            "user_id": 644,
            "created_at": "2018-01-11T17:09:07.926Z",
            "updated_at": "2018-01-13T10:53:47.792Z",
            "scheduled_at": [
                "2018-02-01T00:00:00Z"
            ]
        }
    ]
}
```

## Create campaign
```
POST dev.golfconnect24.com/api/v2/notify/campaigns/
```

### Permission

- Admin account

### Params

	- `title` < string
	- `gender` < string (`F`  female, `M` male, `-` all)
	- `age_min` < int (optional, default `18`)
	- `age_max` < int (optional, default `70`)
	- `scheduled_at` < string[] (datetime format ISO8601)
	- `city_ids` < string|int[] (list of city ID, ex: `"1,2,3"` or `[1, 2, 3]`)

### Response
- 200 If success
- 400 If client error (invalid data, validate error)
- 500 If server error

## Update campaign
```
PUT dev.golfconnect24.com/api/v2/notify/campaigns/CAMPAIGN_ID
```

### Permission

- Admin account

### Params & Response

- `CAMPAIGN_ID` < int: ID of campaign to edit

_other params & response like creating_

## Delete Campaign
```
DELETE dev.golfconnect24.com/api/v2/notify/campaigns/CAMPAIGN_ID
```

### Permission

- Admin account

### Params

- `CAMPAIGN_ID` < int: ID of campaign to delete

### Response
- 200 If success
- 500 If server error

## Get History Campaigns

```
GET dev.golfconnect24.com/api/v2/notify/campaigns/history/
```

### Permission

- Admin account

### Response
- 200 If success
- 401 If unauthorized
- 500 If server error

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "hello",
            "body": "hello",
            "gender": "-",
            "age_min": 18,
            "age_max": 70,
            "city_ids": "",
            "sent_at": "2018-01-19T23:20:31Z",
            "user_id": 644,
            "created_at": "2018-01-11T17:09:07.926Z",
            "updated_at": "2018-01-13T10:53:47.792Z",
            "scheduled_at": [
                "2018-02-01T00:00:00Z"
            ]
        }
    ]
}
```

### Get Notify Logs

```
GET dev.golfconnect24.com/api/v2/notify/logs/
```

### Permission

- Valid user account

### Params

- `user_id`  < int: User Id to get logs (if user admin token, default uses id of current user linked to token)
- `page` < int: for pagination (default `1`)

### Response

- 200 If success
- 401 If unauthorized
- 500 If server error

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "schedule_id": 2,
            "user_id": 12,
            "sent_at": "2018-01-13T10:53:47.528Z",
            "title": "hello",
            "body": "hello"
        }
    ]
}
```
