package com.neom.oxagon.sap;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Minimal OData v4 client targeting SAP S/4HANA Cloud APIs.
 *
 * Handles:
 *  - OAuth2 client_credentials bearer token acquisition + caching
 *  - $select / $filter / $top / $skiptoken query composition
 *  - server-driven paging via @odata.nextLink
 *
 * NOTE: For brevity this is a stub of the production client; the real
 * implementation lives behind Apache Olingo's EdmEnabledODataClient.
 */
@Component
public class OData4Client {

    private static final Logger log = LoggerFactory.getLogger(OData4Client.class);

    private final HttpClient http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .build();

    @Value("${oxagon.sap.base-url}")
    private String baseUrl;

    @Value("${oxagon.sap.auth.token-url}")
    private String tokenUrl;

    @Value("${oxagon.sap.auth.client-id}")
    private String clientId;

    @Value("${oxagon.sap.auth.client-secret}")
    private String clientSecret;

    private volatile String cachedToken;
    private volatile Instant tokenExpiry = Instant.EPOCH;

    public HttpResponse<String> get(String entitySet, Map<String, String> queryParams) throws Exception {
        var token = bearerToken();
        var uri = URI.create(baseUrl + entitySet + buildQuery(queryParams));
        var req = HttpRequest.newBuilder(uri)
            .timeout(Duration.ofSeconds(30))
            .header("Authorization", "Bearer " + token)
            .header("Accept", "application/json;odata.metadata=minimal")
            .GET()
            .build();
        log.debug("OData GET {}", uri);
        return http.send(req, HttpResponse.BodyHandlers.ofString());
    }

    public Optional<String> nextLink(String responseBody) {
        // crude extractor; the production code uses Jackson + ObjectMapper.
        var idx = responseBody.indexOf("\"@odata.nextLink\":\"");
        if (idx < 0) return Optional.empty();
        var start = idx + "\"@odata.nextLink\":\"".length();
        var end = responseBody.indexOf("\"", start);
        return Optional.of(responseBody.substring(start, end));
    }

    private synchronized String bearerToken() throws Exception {
        if (cachedToken != null && Instant.now().isBefore(tokenExpiry.minusSeconds(60))) {
            return cachedToken;
        }
        var body = "grant_type=client_credentials"
            + "&client_id=" + clientId
            + "&client_secret=" + clientSecret;
        var req = HttpRequest.newBuilder(URI.create(tokenUrl))
            .header("Content-Type", "application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build();
        var resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) {
            throw new IllegalStateException("SAP OAuth2 token endpoint returned " + resp.statusCode());
        }
        // simplistic parse (production: Jackson)
        cachedToken = extract(resp.body(), "access_token");
        var ttl = Long.parseLong(extract(resp.body(), "expires_in"));
        tokenExpiry = Instant.now().plusSeconds(ttl);
        return cachedToken;
    }

    private static String extract(String json, String field) {
        var marker = "\"" + field + "\":";
        var i = json.indexOf(marker) + marker.length();
        while (i < json.length() && (json.charAt(i) == ' ' || json.charAt(i) == '"')) i++;
        var j = i;
        while (j < json.length() && json.charAt(j) != '"' && json.charAt(j) != ',' && json.charAt(j) != '}') j++;
        return json.substring(i, j);
    }

    private static String buildQuery(Map<String, String> params) {
        if (params == null || params.isEmpty()) return "";
        var sb = new StringBuilder("?");
        params.forEach((k, v) -> sb.append(k).append('=').append(v).append('&'));
        sb.setLength(sb.length() - 1);
        return sb.toString();
    }
}
