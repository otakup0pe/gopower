![Maintenance](https://img.shields.io/maintenance/yes/2026.svg)

Go Power Bluetooth CLI
=====================

The `gopower_cli.py` script is a basic read-only view into the status of Bluetooth enabled Go Power [Solar Controllers](https://gopowersolar.com/product-category/solar-controllers/). It supports two modes of outputting data;

* Simple Text Output
* Prometheus [textfile](https://github.com/prometheus/node_exporter?tab=readme-ov-file#textfile-collector) collector output

The only configuration required is the setting of the `GOPOWER_ADDR` environment variable with the MAC address of your solar controller. You can find this using any number of Bluetooth exploration tools on a mobile device. Optionally the `GOPOWER_PROMFILE` environment variable may be set to override the default prometheus textfile location of `/var/run/promnode/textfiles/gopower.prom`.

License
-----

[MIT](https://github.com/otakup0pe/hcvswitch/blob/master/LICENSE)

Author
-----
This Go Power CLI was created by [Jonathan Freedman](http://jonathanfreedman.bio/) to provide insight into how sunbeams are being consumed while living off grid in the desert.

