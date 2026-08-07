---
title: Keycloak Auth Service
created: 2026-06-19
updated: 2026-08-08
type: concept
tags: [sdk, integration, security, api, config]
sources: []
confidence: low
---

> **Source status (2026-08-08):** The `docmesh-py-core` raw captures previously cited by this page were removed during wiki cleanup. Re-ingest an authoritative source before relying on these implementation-specific claims.

# Keycloak Auth Service

`KeycloakAuthService`는 `docmesh-py-core`에서 Keycloak access token 발급과 JWT 검증/사용자 정보 추출을 담당하는 인증 중심 public API다. 생성 시 `allowed_algorithms` 같은 검증 제약을 주입할 수 있으며, 소비 프로젝트는 이를 통해 토큰 발급 경로와 bearer 검증 경로를 공통화할 수 있다.

## Token issuance

`fetch_access_token(scope=None)`은 Keycloak token endpoint에서 `client_credentials`와 `password` grant를 지원하며 `AccessTokenResult`를 반환한다. 반환값에는 `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`가 포함되고, 설정 오류/인증 실패/일시 오류/기타 토큰 오류를 구분하는 예외 계층(`KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`)이 제공된다.

## Configuration requirements

v0.2.0 config reference는 Keycloak 영역을 discovery/auth, 토큰 획득, 프로비저닝으로 나눈다. `KeycloakConfig`는 `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`를 요구하며 confidential client 기본값에서는 `KEYCLOAK_CLIENT_SECRET`도 필요하다. password grant는 설정 로딩 시 username/password를 강제하지 않고, `fetch_access_token()` 호출에서 함수 인자 우선으로 완전한 자격증명을 확인한다. 프로비저닝 활성화 시에는 service account secret 또는 관리자 username/password 중 정확히 하나의 Admin API 인증 세트를 요구하며, production에서는 SSL 검증 비활성화를 허용하지 않는다.

## JWT validation

`extract_user_info(token)`은 `Bearer <token>` 형식도 허용하면서 알고리즘, 서명, issuer, expiry, audience를 검증한 뒤 `AuthenticatedUser`를 반환한다. 문서는 RS256 검증 시 JWKS 캐시 TTL 만료 후 재조회와 key rotation 감지 시 1회 강제 refresh까지 명시하므로, 이 API는 단순 claim 파싱보다 운영 환경의 검증 안정성을 중시하는 설계로 볼 수 있다.

## Provisioning boundary

같은 영역의 `KeycloakProvisioner`는 realm/client/role 상태를 원하는 선언으로 수렴시키지만, 실제 Admin API 호출은 외부 `admin_client` 구현에 위임한다. 즉 인증 소비 API와 admin provisioning API를 분리해 두었고, 이는 [[service-factory-registry]] 및 [[service-health-orchestration]]과는 다른 제어면(control plane) 성격의 경계다.

## Related pages

- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[service-health-orchestration]]
