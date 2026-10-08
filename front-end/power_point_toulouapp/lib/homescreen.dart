

import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:power_point_toulouapp/services/mapservice.dart';

class HomeScreen extends StatefulWidget {


  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class  _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
  }  

  @override
  Widget build(BuildContext context) {
    
    final Size size = MediaQuery.sizeOf(context);
    final double width = size.width;
    final double height = size.height;
    final double map_height = 0.8*height;

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 80,
        backgroundColor: Colors.blueAccent,
        title: Image.asset(
            'assets/icons/side_logo.png',
            height : 80, 
        ),
      ),
      body: Center(
        child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            height: map_height,
            width: double.infinity,
            child: MapBuilder(zoom: 15.0, center: LatLng(37.979612645611425, 23.782699894844303)),
        ),
      )
    );
  }
  
}