# RequestBin
Simple request bin on flask

Run it behind any reverse proxy, if base url isn't `/`, provide `X-Script-Name` header.

Example location for nginx: 

```
location /request_bin {
	proxy_pass http://request_bin:5000;
	proxy_set_header Host $host;
	proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	proxy_set_header X-Scheme $scheme;
	proxy_set_header X-Script-Name /request_bin;
}
```
