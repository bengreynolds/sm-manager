# X Planning

Status: roadmap only

Do not implement this platform until explicitly approved by the user.

## Objective

Add a Twitter/X adapter after Instagram is stable, using the official X API for media upload and post publishing.

## Expected Scope

- account connection
- media upload
- post publishing
- shared scheduler integration
- shared audit and retry handling

## Constraints

- validate current access tier and rate-limit requirements before implementation
- use official media upload and publish flows
- keep media upload logic isolated from other platform adapters

## Planned Work

1. confirm current API access requirements
2. implement account token handling
3. implement chunked media upload path for video
4. implement post publish workflow
5. wire into shared scheduler and UI

## References

- X media upload overview: https://developer.x.com/en/docs/x-api/v1/media/upload-media/overview
- X media upload endpoint: https://developer.x.com/en/docs/x-api/v1/media/upload-media/api-reference/post-media-upload
- X chunked upload init: https://developer.x.com/en/docs/x-api/v1/media/upload-media/api-reference/post-media-upload-init
- X chunked upload finalize: https://developer.x.com/en/docs/x-api/v1/media/upload-media/api-reference/post-media-upload-finalize
